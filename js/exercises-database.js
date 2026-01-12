// Exercise Database - All Practice Exercises
// This database contains all exercises with their solutions for AI agent context

const ALL_EXERCISES = [
  {
    id: 'loading-california-housing-dataset',
    title: 'Loading California Housing Dataset',
    chapter: 'Chapter 2: Business Analytics Foundations',
    difficulty: 'easy',
    description: 'Practice exercise from Chapter 2: Business Analytics Foundations',
    solutionCode: `from sklearn.datasets import fetch_california_housing

california_housing = fetch_california_housing()

X = california_housing.data
y = california_housing.target

print(X)
print(y)`
  },
  {
    id: 'exploring-dataset-structure',
    title: 'Exploring Dataset Structure',
    chapter: 'Chapter 2: Business Analytics Foundations',
    difficulty: 'easy',
    description: 'Practice exercise from Chapter 2: Business Analytics Foundations',
    solutionCode: `columns = california_housing.feature_names
print(columns)

target = california_housing.target_names
print(target)`
  },
  {
    id: 'dataframe-creation',
    title: 'DataFrame Creation',
    chapter: 'Chapter 2: Business Analytics Foundations',
    difficulty: 'easy',
    description: 'Practice exercise from Chapter 2: Business Analytics Foundations',
    solutionCode: `import pandas as pd

california_df = pd.DataFrame(data = X, columns= columns)

california_df.head(10)`
  },
  {
    id: 'dataset-exploration',
    title: 'Dataset Exploration',
    chapter: 'Chapter 2: Business Analytics Foundations',
    difficulty: 'easy',
    description: 'Practice exercise from Chapter 2: Business Analytics Foundations',
    solutionCode: `california_df.shape`
  },
  {
    id: 'data-types-and-structure',
    title: 'Data Types and Structure',
    chapter: 'Chapter 2: Business Analytics Foundations',
    difficulty: 'easy',
    description: 'Practice exercise from Chapter 2: Business Analytics Foundations',
    solutionCode: `california_df.dtypes`
  },
  {
    id: 'handling-missing-values',
    title: 'Handling Missing Values',
    chapter: 'Chapter 4: Data Collection and Preparation',
    difficulty: 'medium',
    description: 'Practice exercise from Chapter 4: Data Collection and Preparation',
    solutionCode: `california_df.isnull()

california_df.isnull().sum()

california_df.isna()

california_df.isna().sum()

import numpy as np

def introduce_missing_values(df, fraction_missing, random_state=None):
    np.random.seed(random_state)
    mask = np.random.rand(*df.shape) < fraction_missing
    df_with_missing = df.mask(mask)
    return df_with_missing

df_with_missing = introduce_missing_values(california_df, 0.2, random_state=42)

df_with_missing.isna().sum()`
  },
  {
    id: 'outlier-detection-and-removal',
    title: 'Outlier Detection and Removal',
    chapter: 'Chapter 4: Data Collection and Preparation',
    difficulty: 'medium',
    description: 'Practice exercise from Chapter 4: Data Collection and Preparation',
    solutionCode: `california_df.boxplot()

def count_outliers(column):
    if pd.api.types.is_numeric_dtype(column):
        Q1 = column.quantile(0.25)
        Q3 = column.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = column[(column < lower_bound) | (column > upper_bound)]
        return outliers.shape[0]
    else:
        return 0

def remove_outliers(column):
    Q1 = column.quantile(0.25)
    Q3 = column.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    column = column[(column >= lower_bound) & (column <= upper_bound)]
    return column

california_df_clean = california_df.copy()
for column in california_df_clean.select_dtypes(include=['number']).columns:
    california_df_clean[column] = remove_outliers(california_df_clean[column])

california_df_clean = california_df_clean.dropna()`
  },
  {
    id: 'data-standardization',
    title: 'Data Standardization',
    chapter: 'Chapter 4: Data Collection and Preparation',
    difficulty: 'medium',
    description: 'Practice exercise from Chapter 4: Data Collection and Preparation',
    solutionCode: `import pandas as pd
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()

numeric_columns = california_df.select_dtypes(include=['number'])

california_df_standardized = scaler.fit_transform(numeric_columns)

california_df_standardized = pd.DataFrame(california_df_standardized, columns=numeric_columns.columns)`
  },
  {
    id: 'data-normalization',
    title: 'Data Normalization',
    chapter: 'Chapter 4: Data Collection and Preparation',
    difficulty: 'medium',
    description: 'Practice exercise from Chapter 4: Data Collection and Preparation',
    solutionCode: `from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler()

numeric_columns = california_df.select_dtypes(include=['number'])

california_df_scaled = scaler.fit_transform(numeric_columns)

california_df_scaled = pd.DataFrame(california_df_scaled, columns=numeric_columns.columns)`
  }
  // Note: Additional exercises from other chapters can be added here
  // The database can be expanded as more exercises are added to practice.html
];

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ALL_EXERCISES;
}
