import threading
import time
import numpy as np
import librosa

from enum import Enum, auto

class NormalizationMethod(Enum):
    NONE = auto()
    MIN_MAX = 'Min-Max'
    MEAN = 'Mean'
    Z_SCORE = 'Z-Score'
    ROBUST = 'Robust'

class NormalizationMethods:
    def __init__(self, method: NormalizationMethod = NormalizationMethod.NONE):
        self.normalization_method = method

    @staticmethod
    def minMax_normalization(params):
        '''This method scales the data to fit within the range [0, 1] or [-1, 1]'''
        min_params = np.min(params)
        max_params = np.max(params)
        return (params - min_params) / (max_params - min_params)
    
    @staticmethod
    def mean_normalization(params):
        '''This normalization method centers the data around zero by subtracting the mean.'''
        mean_params = np.mean(params, axis=1, keepdims=True)
        return params - mean_params
    
    @staticmethod
    def standardize_normalization(params):
        '''This normalization method involves scaling the data so it has a mean of 0 and a standard deviation of 1'''
        mean_params = np.mean(params, axis=1, keepdims=True)
        std_params = np.std(params, axis=1, keepdims=True)
        return (params - mean_params) / std_params
    
    @staticmethod
    def robust_normalization(params):
        '''This method uses the median and the interquartile range instead of the mean and standard deviation,
         reducing the influence of outliers.'''
        median_params = np.median(params, axis=1, keepdims=True)
        iqr_mfcc = np.percentile(params, 75, axis=1, keepdims=True) - np.percentile(params, 25, axis=1, keepdims=True)
        return (params - median_params) / iqr_mfcc
    
    def apply_normalization(self, params):
        if self.normalization_method == NormalizationMethod.MIN_MAX:
            return self.minMax_normalization(params)
        elif self.normalization_method == NormalizationMethod.MEAN:
            return self.mean_normalization(params)
        elif self.normalization_method == NormalizationMethod.Z_SCORE:
            return self.standardize_normalization(params)
        elif self.normalization_method == NormalizationMethod.ROBUST:
            return self.robust_normalization(params)
        else:
            return params  # If NONE or any other case, don't apply normalization

    

class AudioFeatureExtractor(threading.Thread):
    def __init__(self, circular_buffer, sample_rate, channels, callback, normalization_method: NormalizationMethod):
        threading.Thread.__init__(self)
        self.circular_buffer = circular_buffer
        self.sample_rate = sample_rate
        self.channels = channels
        self.normalization_method = normalization_method
        self.callback = callback
        self.running = True

    def run(self):
        while self.running:
            if len(self.circular_buffer.buffer) > 0:
                audio_feature = self.extract_features()
                self.callback(audio_feature)
            time.sleep(0.005)  # Adjust sleep time based on your needs

    def stop(self):
        self.running = False

    def extract_features(self):
        pass

    
class MFCCFeatureExtractor(AudioFeatureExtractor):
    def __init__(self, circular_buffer, sample_rate, channels, callback, normalization_method: NormalizationMethod):
        super().__init__(circular_buffer, sample_rate, channels, callback, normalization_method)
    
    def extract_features(self):
        audio_data = self.circular_buffer.get()
        mfcc = librosa.feature.mfcc(y=audio_data, sr=self.sample_rate, n_mfcc=8)
        mfcc = mfcc[2:,:]
        mfcc = mfcc.mean(axis=1)
        
        # Apply normalization according to the specified method
        normalizer = NormalizationMethods(self.normalization_method)
        return normalizer.apply_normalization(mfcc)

