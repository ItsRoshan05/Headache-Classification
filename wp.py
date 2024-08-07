# Fungsi WP (Weight Product)
import numpy as np
import pandas as pd

def normalize_weights(weights):
    total_weight = sum(weights)
    return [w / total_weight for w in weights]

def calculate_weighted_product(weights, values):
    weighted_values = values ** weights
    return np.prod(weighted_values, axis=1)

def load_data(age_group):
    csv_file = 'data/dataset_adult.csv' if age_group == 1 else 'data/dataset_child.csv'
    return pd.read_csv(csv_file)

def validate_columns(df, required_columns):
    return all(col in df.columns for col in required_columns)

def map_age_group(value):
    if value == '1':
        return 1
    elif value == '2':
        return 2
    return 'Unknown'