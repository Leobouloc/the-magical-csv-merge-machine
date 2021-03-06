#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 24 19:18:44 2017

@author: leo

AbstractDataProject

METHODS:
    
    - init_log(self, module_name, module_type)
    - end_log(self, log, error=False)
    - check_mem_data(self)
    - load_data(self, module_name, file_name, nrows=None, columns=None)
    - get_header(self, module_name, file_name)
    - get_sample(self, sampler_module_name, params, sample_params)
    - write_log_buffer(self, written)
    - write_run_info_buffer(self)
    - write_data(self)
    - clear_memory(self)
    - infer(self, module_name, params)

"""

import csv
import gc
import os
import time

import numpy as np
import pandas as pd

from abstract_project import AbstractProject, NOT_IMPLEMENTED_MESSAGE

from MODULES import MODULES

class AbstractDataProject(AbstractProject):
    '''
    Allows loading and writing of data objects (pandas DataFrames) and 
    anticipates usage of transformations and writing them to log
    '''
    
    def __init__(self, 
                 project_id=None, 
                 create_new=False, 
                 description=None,
                 display_name=None):
        super().__init__(project_id=project_id, 
                          create_new=create_new, 
                          description=description,
                          display_name=display_name)
        # Initiate with no data in memory
        self.mem_data = None
        self.mem_data_info =  dict() # Information on data in memory
        self.run_info_buffer = dict()
        self.log_buffer = [] # List of logs not yet written to metadata.json    
    
    
    def init_log(self, module_name, module_type):
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)
        
    def upload_init_data(self, file, file_name, user_given_name=None):
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def end_log(self, log, error=False):
        '''
        Close a log mesage started with init_log (right after module call)
        '''
        log['end_timestamp'] = time.time()
        log['error'] = error
        return log    
    
    def check_mem_data(self):
        '''Check that there is data loaded in memory'''
        if self.mem_data is None:
            raise Exception('No data in memory: use `load_data` (reload is \
                        mandatory after dedupe)')
        
    def load_data(self, module_name, file_name, nrows=None, columns=None):
        '''Load data as pandas DataFrame to memory. Overwritten in normalize'''
        file_path = self.path_to(module_name, file_name)
        if nrows is not None:
            print('Nrows is : ', nrows)
            self.mem_data = pd.read_csv(file_path, encoding='utf-8', dtype=str, nrows=nrows, usecols=columns)
        else:
            self.mem_data = pd.read_csv(file_path, encoding='utf-8', dtype=str, usecols=columns)
        self.mem_data_info = {'file_name': file_name,
                              'module_name': module_name}


    def get_sample(self, sampler_module_name, module_params, sample_params):
        '''
        Returns an interesting sample for the data and config at hand.
        
        NB: This is here for uniformity with transform and infer
        
        INPUT:
            - sampler_module_name: name of sampler function (None for first N
                                                             rows)
            - module_params: inference params to send to sampler to help with selection
            - sample_params: parameters concerning the size of output etc.
        OUTPUT:
            - sample
        
        '''
        self.check_mem_data()
        
        sample_params.setdefault('randomize', True)
        
        # TODO
        if sample_params['randomize']:
            indexes = np.random.permutation(range(self.mem_data.shape[0]))[:20]
            sample_params.setdefault('sample_ilocs', indexes)
        else:
            sample_params.setdefault('sample_ilocs', range(20))
        
        # 
        if sampler_module_name is None:
            sampler_module_name = 'standard'
        
        sample_ilocs = []
        if sampler_module_name != 'standard':
            sample_ilocs = MODULES['sample'][sampler_module_name]['func'](self.mem_data, 
                                                              module_params, sample_params)
        
        # If default sampler was selected custom sampler returned no rows
        if not sample_ilocs:
            sample_ilocs = sample_params.get('sample_ilocs', range(5))
         
        # Transform int to range if int is received
        if isinstance(sample_ilocs, int):
            sample_ilocs = range(sample_ilocs)

        cols_to_display = sample_params.get('cols_to_display', self.mem_data.columns)
        sub_tab = self.mem_data.iloc[sample_ilocs].loc[:, cols_to_display]

        
        if sample_params.get('drop_duplicates', True):
            sub_tab.drop_duplicates(inplace=True)

        # Replace missing values
        sub_tab.fillna('', inplace=True)
        
        #        sample = self._get_sample(module_name, file_name,
        #                                 row_idxs=[0] + [x+1 for x in sample_ilocs])        
        sample = sub_tab.to_dict('records')    
        return sample
        
    def make_mini(self, params):
        '''
        Creates a smaller version of the table in memory. 
        Set mem_data_info and current file to mini
        '''
        # TODO: Change current 
        # TODO: Current for normalize ?        
        self.check_mem_data()
        
         # Set defaults
        sample_size = params.get('sample_size', 5000)
        randomize = params.get('randomize', True)       
        NEW_FILE_NAME = 'MINI__' + self.mem_data_info['file_name']        
        
        
        
        # Only create file if it is larger than sample size
        
        if self.mem_data.shape[0] > sample_size:            
            if self.mem_data_info['module_name'] != 'INIT':
                raise Exception('make_mini can only be called on data in memory from the INIT module')
            self.clean_after('INIT', NEW_FILE_NAME) # TODO: check module_name for clean_after
            
    
            # Initiate log
            log = self.init_log('INIT', 'transform')  # TODO: hack here: module_name should be 'make_mini'
            
            if randomize:
                sample_index = self.mem_data.index[:sample_size]
            else:
                sample_index = np.random.permutation(self.mem_data.index)[:sample_size]
            
            # Replace data in memory
            self.mem_data = self.mem_data.loc[sample_index, :]
            
            # Update metadata and log
            self.metadata['has_mini'] = True
            self.mem_data_info['file_name'] = NEW_FILE_NAME
            log['og_file_name'] = log['file_name']
            log['file_name'] = NEW_FILE_NAME
            
            # TODO: think if transformation should / should not be complete
    
            # Complete log
            log = self.end_log(log, error=False)
                              
            # Update buffers
            self.log_buffer.append(log)
            # TODO: Make sure that run_info_buffer should not be extended
                   
            return log            
        else:
            self.metadata['has_mini'] = False
            return {}
    
    
    def write_log_buffer(self, written):
        '''
        Appends log buffer to metadata, writes metadata and clears log_buffer.
        
        INPUT: 
            - written: weather or not the data was written
        
        '''
        if not self.log_buffer:
            # TODO: Put warning here
            pass
            #            raise Exception('No log buffer: no operations were executed since \
            #                            write_log_buffer was last called')
        
        # Indicate if any data was written
        if written:
            for log in self.log_buffer[::-1]:
                assert log['module_type'] in ['infer', 'transform', 'link']
                if log['module_type'] in ['transform', 'link']:
                    log['written'] = True
                    break
                       
        # Add buffer to metadata  
        self.metadata['log'].extend(self.log_buffer)
    
        # Write metadata and clear log buffer
        self.write_metadata()
        self.log_buffer = []

    def write_run_info_buffer(self):
        '''
        Appends run info buffer to metadata, writes metadata and clears run_info_buffer.        
        '''
        # TODO: run_info should be file_name aware
        for module_name, run_info in self.run_info_buffer.items():
            self.upload_config_data(run_info, module_name, 'run_info.json')
        self.run_info_buffer = dict()
        
    def write_data(self):
        '''Write data stored in memory to proper module'''
        self.check_mem_data()
            
        # Write data
        dir_path = self.path_to(self.mem_data_info['module_name'])
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)        
        file_path = self.path_to(self.mem_data_info['module_name'], 
                                 self.mem_data_info['file_name'])
        self.mem_data.to_csv(file_path, encoding='utf-8', index=False, 
                             quoting=csv.QUOTE_NONNUMERIC)
        print('Wrote to ', file_path)

        
    def clear_memory(self):
        '''Removes the table loaded in memory'''
        self.mem_data = None
        self.mem_data_info = None
        gc.collect()
        
        
    def infer(self, module_name, params):
        '''
        Runs the module on pandas DataFrame data in memory and 
        returns answer + writes to appropriate location
        '''
        self.check_mem_data()  
        
        # Initiate log
        log = self.init_log(module_name, 'infer')
        
        infered_params = MODULES['infer'][module_name]['func'](self.mem_data, params)
        
        # Write result of inference
        module_to_write_to = MODULES['infer'][module_name]['write_to']
        self.upload_config_data(infered_params, module_to_write_to, 'infered_config.json')
        
        # Update log buffer
        self.log_buffer.append(log)     
        
        return infered_params
    
    
    def transform(self, module_name, params):
        '''
        Run module on pandas DataFrame in memory and update memory state.
        /!\ DATA IS CLEANED WHEN transform IS CALLED
        '''
        self.check_mem_data()        
        self.clean_after(module_name, self.mem_data_info['file_name'])
        
        # Initiate log
        log = self.init_log(module_name, 'transform')

        # TODO: catch module errors and add to log
        # Run module on pandas DataFrame 
        self.mem_data, run_info = MODULES['transform'][module_name]['func'](self.mem_data, params)
        self.mem_data_info['module_name'] = module_name
        
        # Transformation -> the project is still_not/ no_longer complete
        self.metadata['complete'][self.mem_data_info['file_name']] = False

        # Complete log
        log = self.end_log(log, error=False)
                          
        # Add time to run_info (# TODO: is this the best way?)
        run_info['params'] = params
        run_info['start_timestamp'] = log['start_timestamp']
        run_info['end_timestamp'] = log['end_timestamp']
        
        # Update buffers
        self.log_buffer.append(log)
        self.run_info_buffer[module_name] = run_info
        
        return log, run_info