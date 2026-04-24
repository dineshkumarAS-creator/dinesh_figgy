import pickle
import os

files = ['lstm_dataset.pkl', 'gbm_dataset.pkl', 'isolation_forest_dataset.pkl']

for f in files:
    if os.path.exists(f'generated_data/{f}'):
        with open(f'generated_data/{f}', 'rb') as fp:
            data = pickle.load(fp)
            print(f'\n=== {f} ===')
            for key, val in data.items():
                if hasattr(val, 'shape'):
                    print(f'  {key}: shape {val.shape}, dtype {val.dtype}')
                else:
                    print(f'  {key}: {type(val).__name__}')
