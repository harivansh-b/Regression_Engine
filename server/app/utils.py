import numpy as np
import pandas as pd
from datetime import datetime
from statsmodels.stats.stattools import durbin_watson as dbw
import statsmodels.api as sm
from scipy.stats import jarque_bera as jb, boxcox
import matplotlib.pyplot as plt
from statsmodels.stats.diagnostic import het_breuschpagan
from scipy.stats import zscore
from statsmodels.stats.outliers_influence import variance_inflation_factor as vif
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import font_manager
import os
import matplotlib
from matplotlib.colors import LinearSegmentedColormap
matplotlib.use('Agg')
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score as r2
from sklearn.metrics import mean_absolute_error as mae
from statsmodels.stats.outliers_influence import variance_inflation_factor

import base64

def to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
    
def encode_image_to_base64(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
    
def treat_null(df,col,method,value=None):
    try:
        if method==1: #drop null values
            df.dropna(subset=[col],inplace=True)

        elif method==2: #fill with give values
            if value is None:
                raise ValueError("No values provided")
            
            if not (pd.api.types.is_numeric_dtype(df[col]) and isinstance(value,(int,float))
                or (df[col].dtype == object or pd.api.types.is_string_dtype(df[col])) and isinstance(value, str)
                or pd.api.types.is_datetime64_any_dtype(df[col]) and isinstance(value,datetime)):
                    raise ValueError("Value miss match in columns and given values")
            else:
                    df[col]=df[col].fillna(value)

        elif method==3: #forward fill
            df[col]=df[col].fillna(method='ffill')

        elif method==4: #backward fill
            df[col]=df[col].fillna(method='bfill') 

        elif method==5: #mean for numeric data and mode for other types
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col]=df[col].fillna(df[col].mean())
            else:
                df[col]=df[col].fillna(df[col].mode()[0])

        elif method==6: #median for numeric data and mode for other types
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col]=df[col].fillna(df[col].median())
            else:
                df[col]=df[col].fillna(df[col].mode()[0])
        else:
            raise ValueError('Invalid Option')
      
    except ValueError as e:
        print(e)
    except IndexError as e:
        print(e)
    finally:
        return df
    
def treat_outliers(df, method, features,model=None):
    try:
        if method == 1:
            # Cook's Distance (requires model)
            if model is None:
                raise ValueError("Model is required for method 1 (Cook's Distance)")
            influence = model.get_influence()
            cooks_d, _ = influence.cooks_distance
            outliers = np.where(cooks_d > 1)[0].tolist()

        elif method == 2:
            # IQR method
            if features is None:
                features = df.select_dtypes(include=[np.number]).columns

            outlier_indices = set()

            for col in features:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    continue  # Skip non-numeric columns

                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                outliers_in_col = df[(df[col] < lower_bound) | (df[col] > upper_bound)].index
                outlier_indices.update(outliers_in_col)

            outliers = list(outlier_indices)
        elif method == 3:
            # Z-score method
            zscores = df.select_dtypes(include=[np.number]).apply(zscore)
            outlier_rows = (zscores.abs() > 3).any(axis=1)
            outliers = df[outlier_rows].index.tolist()

        else:
            raise ValueError("Invalid Option: method must be 1 (Cook), 2 (IQR), or 3 (Z-score)")

    except ValueError as e:
        print("ValueError:", e)
        outliers = []

    return df.drop(index=outliers).reset_index(drop=True)


def get_correlation_matrix(df,target,feature):
    return df[target,*feature].corr()
#diagnose
def get_correlation_feature(df, target, feature):
    res = {}
    for feat in feature:
        try:
            if df[feat].dtype.kind in 'bifc' and df[feat].std() != 0 and df[target].std() != 0:
                corr_value = df[feat].corr(df[target])
                res[feat] = corr_value if not np.isnan(corr_value) else 0
            else:
                res[feat] = 0
        except Exception as e:
            print(f"Error processing {feat}: {e}")
            res[feat] = 0
    return res
#assumption-1 Linearity of feature-target relationship
def linearity_test(df, target, feature, one_hot):
    failed = []
    res = get_correlation_feature(df, target, feature)
    for key, value in res.items():
        if key=="const" or key in one_hot:
            continue
        if abs(value) < 0.1:
            failed.append(key)
    if not failed:
        return {'result': 'success'}
    else:
        return {'result': 'failure', 'features': failed}
    
#assumption-2 Independence of errors
def independence_of_errors_test(model):
    test_val=dbw(model.resid)
    return {
        'result':'success' if 1.5<test_val<2.5 else 'failure',
        'test_val_dbw':float(test_val)
    }

#assumption-3 Normality of errors
def normality_of_errors_test(model):
    stat,p=jb(model.resid)
    
    return {
        'result':'success' if p > 0.05 else 'failure',
        'test_val_jb':float(p)
    }

#assumption-4 No Perfect Multicollinearity
def perfect_multicollinearity_test(df, features, threshold=5.0):
    X = df[features].copy()

    # Drop constant columns (zero variance)
    constant_cols = [col for col in X.columns if X[col].std() == 0]
    X.drop(columns=constant_cols, inplace=True)

    # Drop one dummy column from each one-hot group
    dummy_like = [col for col in X.columns if '_' in col]
    prefix_groups = {}
    for col in dummy_like:
        prefix = col.split('_')[0]
        prefix_groups.setdefault(prefix, []).append(col)

    dropped_dummies = []
    for group in prefix_groups.values():
        if len(group) > 1:
            dropped_dummies.append(group[0])
            X.drop(columns=[group[0]], inplace=True)

    # Add constant
    X = sm.add_constant(X)

    vif_values = {}
    high_vif = []

    for i in range(1, X.shape[1]):  # skip the constant
        try:
            vif_score = variance_inflation_factor(X.values, i)
            col_name = X.columns[i]
            vif_values[col_name] = round(vif_score, 1)
            if vif_score > threshold:
                high_vif.append(col_name)
        except (np.linalg.LinAlgError, ZeroDivisionError):
            col_name = X.columns[i]
            vif_values[col_name] = float('inf')
            high_vif.append(col_name)

    return {
        'result': 'success' if not high_vif else 'failure',
        'vif': vif_values,
        'high_vif_features': high_vif,
        'removed_constant_features': constant_cols,
        'removed_dummy_features': dropped_dummies
    }


def equal_variance_test(model, alpha=0.05):
    try:
        residuals = model.resid
        exog = model.model.exog  # Must include constant + features

        if exog.shape[1] < 2:
            raise ValueError("Exog must have at least two columns including a constant.")

        lm_stat, lm_pval, f_stat, f_pval = het_breuschpagan(residuals, exog)

        return {
            "result": "failure" if lm_pval < alpha else "success",
            "lm_stat": float(lm_stat),
            "f_stat": float(f_stat),
            "p_value": lm_pval
        }

    except Exception as e:
        return {
            "error": str(e)
        }
#Fix
#assumption-1 Linearity of feature-target relationship
def fix_linearity(df,feature,method,degree=2):
    try:
        if method==1: # logarithimic transformation 
            df[f'log({feature})']=np.log(df[feature]+1)
        elif method==2: # exponential transformation
            df[f'exp({feature})']=np.exp(df[feature])
        elif method==3: # polynomial transformation
            for i in range(2,degree+1):
                df[f'__{feature}^{degree}__']= df[feature] ** i
        else:
            raise ValueError('Invalid method')
    except ValueError as e:
        print(e)
    finally:
        return df

#assumption-2 Independence of errors
def fix_independence_of_errors(y,X):
    y=y.sample(frac=1)
    X=X.sample(frac=1)
    return sm.GLS(y,X).fit()

#assumption-3 Normality of errors
def fix_normality_of_errors(df,feature,method):
    try:
        if method==1:
            df[f'log({feature})']=np.log(df[feature]+1)
        elif method==2:
            df[f'sqrt({feature})']=np.sqrt(df[feature])
        elif method==3:
            if (df[feature] <= 0).any():
                raise ValueError("value can't be negative for boxcox transformation")
            df[f'boxcox({feature})'],_=boxcox(df[feature])
    except ValueError as e:
        print(e)
    finally:
        return df
    
#assumption-4 No Perfect Multicollinearity
def fix_perfect_collinearity(df, method, feature):
    try:
        if len(method) != len(feature):
            raise IndexError("Length of columns and methods to resolve are different")

        for i in range(len(method)):
            if method[i] == 1:
                continue  # Keep the feature
            elif method[i] == 2:
                df.drop(columns=[feature[i]], inplace=True)  # Drop the feature
            else:
                raise ValueError("Invalid Option: Only 1 (keep) or 2 (drop) allowed")

    except ValueError as e:
        print("ValueError:", e)
    except IndexError as e:
        print("IndexError:", e)
    finally:
        return df

#assumption-5 Equal Variance of errors
def fix_equal_variance_test(df,method,feature):
    try:
        if method==1:
            df[f'log({feature})']=np.log(df[feature]+1)
        elif method==2:
            df[f'sqrt({feature})']=np.sqrt(df[feature])
        elif method==3:
            if (df[feature] <= 0).any():
                raise ValueError("value can't be negative for boxcox transformation")
            df[f'boxcox({feature})'],_=boxcox(df[feature])
    except ValueError as e:
        print(e)
    finally:
        return df

def get_category_vars(df):
    res={}
    for col in df.columns:
        if df[col].dtype==object :
            res[col]=list(df[col].unique())
    return res

def get_attributes(df):
    res = {}
    for col in df.columns:
        res[col] = True if pd.api.types.is_numeric_dtype(df[col]) else df[col].mode()[0]
    return res

def to_dataframe(filepath,format):
    if format=='json':
        return pd.read_json(filepath)
    else:
        return pd.read_csv(filepath)
    
def from_dataframe(df,format):
    if format=='json':
        return df.to_json(orient='records')
    else:
        return df.to_csv('data.csv')

def bayesian_target_encoding(x, y, feature, alpha=5):
    temp = pd.DataFrame({feature: x, 'target': y})
    overall_mean = y.mean()
    agg = temp.groupby(feature)['target'].agg(['mean', 'count'])
    agg['encoded'] = (agg['mean'] * agg['count'] + overall_mean * alpha) / (agg['count'] + alpha)
    mapping = agg['encoded']
    return x.map(mapping), mapping

def preprocess_onehot(x, ignore_first=False):
    features=[]
    res = pd.DataFrame(index=x.index)
    onehot_mapping = {}
    high_cardinality_cols = []

    for col in x.columns:
        if pd.api.types.is_numeric_dtype(x[col]):
            res[col] = x[col]
        else:
            unique_vals = x[col].nunique()
            if unique_vals == 1:
                res[col] = 1
                unique_val=list(x[col].unique())
                onehot_mapping[col] = unique_val
                features.append(unique_val)
            elif 1 < unique_vals < 10:
                unique_categories = list(x[col].unique())
                onehot_mapping[col] = unique_categories
                if ignore_first:
                    unique_categories = unique_categories[1:]
                features.extend(unique_categories)
                for val in unique_categories:
                    res[f'{col}_{val}'] = (x[col] == val).astype(int)
            else:
                high_cardinality_cols.append(col)
                features.append(col)

    return res, high_cardinality_cols, onehot_mapping,features

def visualize_before_outliers(uid,features,df):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    font_path = os.path.join(base_dir, 'static', 'fonts', 'Montserrat-Regular.ttf')
    font_prop = font_manager.FontProperties(fname=font_path)

    for feature in features:
        if not pd.api.types.is_numeric_dtype(df[feature]):
            continue  # Skip non-numeric columns
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=df[feature] , color="#a86de7")
        plt.title(f'{feature}')
        plt.tight_layout()
        save_dir = os.path.join(base_dir, 'static', 'images','before_removing_outliers')
        os.makedirs(save_dir, exist_ok=True)

        filename = os.path.join(save_dir, f'{uid}{feature}.jpeg')
        plt.savefig(filename, dpi=300)
        plt.close()

def visualize_after_outliers(uid,features,df):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    font_path = os.path.join(base_dir, 'static', 'fonts', 'Montserrat-Regular.ttf')
    font_prop = font_manager.FontProperties(fname=font_path)

    for feature in features:
        if not pd.api.types.is_numeric_dtype(df[feature]):
            continue  # Skip non-numeric columns
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=df[feature] , color="#a86de7")
        plt.title(f'{feature}')
        plt.tight_layout()
        save_dir = os.path.join(base_dir, 'static', 'images','after_removing_outliers')
        os.makedirs(save_dir, exist_ok=True)

        filename = os.path.join(save_dir, f'{uid}{feature}.jpeg')
        plt.savefig(filename, dpi=300)
        plt.close()

def visualize_linearity(uid, df, target, features,onehot):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    font_path = os.path.join(base_dir, 'static', 'fonts', 'Montserrat-Regular.ttf')
    font_prop = font_manager.FontProperties(fname=font_path)

    for feature in features:
        if feature == 'const' or feature in onehot:
            continue
        plt.figure(figsize=(6, 4))
        sns.regplot(data=df, 
                    x=feature, 
                    y=target,
                    scatter_kws={'color': "#a86de7", 'alpha': 0.5},  
                    line_kws={'color': '#7604f1', 'alpha': 1.0} )
        plt.title(f'{feature} vs {target}', fontproperties=font_prop)
        plt.xlabel(feature, fontproperties=font_prop)
        plt.ylabel(target, fontproperties=font_prop)
        ax = plt.gca()
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(font_prop)
        plt.tight_layout()
        save_dir = os.path.join(base_dir, 'static', 'images', 'assumption_1')
        os.makedirs(save_dir, exist_ok=True)

        filename = os.path.join(save_dir, f'{uid}{feature}vs{target}.jpeg')
        plt.savefig(filename, dpi=300)
        plt.close()

def visualize_independence_error(uid, y_pred, residuals):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    font_path = os.path.join(base_dir, 'static', 'fonts', 'Montserrat-Regular.ttf')
    font_prop = font_manager.FontProperties(fname=font_path)


    plt.figure(figsize=(6, 4))
    sns.regplot( x=y_pred, 
                y=residuals,
                scatter_kws={'color': "#a86de7", 'alpha': 0.5})
    plt.axhline(0, linestyle='--', color='#7604f1', linewidth=1)
    plt.title("Residuals vs Fitted Values (Check Error Independence)", fontproperties=font_prop)
    plt.xlabel("Fitted value", fontproperties=font_prop)
    plt.ylabel("Residuals", fontproperties=font_prop)
    ax = plt.gca()
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(font_prop)
    plt.tight_layout()
    save_dir = os.path.join(base_dir, 'static', 'images', 'assumption_2')
    os.makedirs(save_dir, exist_ok=True)

    filename = os.path.join(save_dir, f'{uid}.jpeg')
    plt.savefig(filename, dpi=300)
    plt.close()

def plot_residual_histogram(uid,residuals):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    font_path = os.path.join(base_dir, 'static', 'fonts', 'Montserrat-Regular.ttf')
    font_prop = font_manager.FontProperties(fname=font_path)

    plt.figure(figsize=(6, 4))
    sns.histplot(residuals, kde=True, color="#a86de7")
    plt.title("Histogram of Residuals (Normality Check)")
    plt.xlabel("Residuals")
    plt.ylabel("Frequency")
    plt.axvline(0, linestyle='--', color='#7604f1')

    ax = plt.gca()
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(font_prop)

    plt.tight_layout()
    save_dir = os.path.join(base_dir, 'static', 'images', 'assumption_3')
    os.makedirs(save_dir, exist_ok=True)

    filename = os.path.join(save_dir, f'{uid}.jpeg')
    plt.savefig(filename, dpi=300)
    plt.close()


def plot_correlation_heatmap(uid, df, features):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    font_path = os.path.join(base_dir, 'static', 'fonts', 'Montserrat-Regular.ttf')
    font_prop = font_manager.FontProperties(fname=font_path)

    plt.figure(figsize=(8, 6))
    corr_matrix = df[features].corr()
    custom_cmap = LinearSegmentedColormap.from_list("custom_purple", ["#ffffff", "#a86de7"])
    sns.heatmap(corr_matrix, cmap = 'Purples' , center=0)
    plt.title("Correlation Matrix (Check Multicollinearity)",fontproperties=font_prop)
    ax = plt.gca()
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(font_prop)
    plt.tight_layout()
    save_dir = os.path.join(base_dir, 'static', 'images', 'assumption_4')
    os.makedirs(save_dir, exist_ok=True)

    filename = os.path.join(save_dir, f'{uid}.jpeg')
    plt.savefig(filename, dpi=300)
    plt.close()

def plot_equal_variance(uid,y_pred, residuals):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    font_path = os.path.join(base_dir, 'static', 'fonts', 'Montserrat-Regular.ttf')
    font_prop = font_manager.FontProperties(fname=font_path)

    plt.figure(figsize=(6, 4))
    sns.scatterplot(x=y_pred, y=residuals, color='#a86de7', alpha=0.6)
    plt.axhline(0, color='#7604f1', linestyle='--', linewidth=1)
    plt.title("Residuals vs Fitted Values (Check Equal Variance)", fontproperties=font_prop)
    plt.xlabel("Fitted Values (Predicted)", fontproperties=font_prop)
    plt.ylabel("Residuals (y - ŷ)", fontproperties=font_prop)
    ax = plt.gca()
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(font_prop)

    plt.tight_layout()
    save_dir = os.path.join(base_dir, 'static', 'images', 'assumption_5')
    os.makedirs(save_dir, exist_ok=True)

    filename = os.path.join(save_dir, f'{uid}.jpeg')
    plt.savefig(filename, dpi=300)
    plt.close()

def cross_validation(X,y):
    kf=KFold(n_splits=5, shuffle=True, random_state=42)
    r2s=[]
    maes=[]

    for train_ind, val_ind in kf.split(X,y):
        X_train,y_train=X.iloc[train_ind],y.iloc[train_ind]
        X_val, y_val=X.iloc[val_ind], y.iloc[val_ind]

        model=sm.OLS(y_train,X_train).fit()

        r2s.append(r2(y_val,model.predict(X_val),))
        maes.append(mae(y_val, model.predict(X_val),))
    
    res = {
        'all_r2s': [round(x, 3) for x in r2s],
        'cross_r2': f'{round(np.mean(r2s), 3)} ± {round(np.std(r2s), 3)}',

        'all_maes': [round(x, 3) for x in maes],
        'cross_mae': f'{round(np.mean(maes), 3)} ± {round(np.std(maes), 3)}'
    }

    return res




def concatenate_df(df1,df2):
    return pd.concat([df1,df2],axis=1)

def make_predictions(model_obj, data):
    test_df = {}

    for key, val in data.items():
        if val['num'] == True:
            test_df[key] = val['value']
        else:
            if key in model_obj.getOneHotMappings():
                categories = model_obj.getOneHotMappings()[key]
                for category in categories:
                    test_df[f'{key}_{category}'] = 1 if category == val['value'] else 0
            elif key in model_obj.getBayesMappings():
                mapping = model_obj.getBayesMappings()[key]
                test_df[key] = mapping.get(val['value'], mapping.mean()) 
            else:
                raise KeyError(f"Invalid attribute or missing encoding for '{key}'")

    model_features = model_obj.getModel().model.exog_names
    if 'const' in model_features:
        test_df['const'] = 1.0
    for col in model_features:
        if col not in test_df:
            test_df[col] = 0

    test_df_df = pd.DataFrame([test_df])[model_features]
    return model_obj.getModel().predict(test_df_df)[0]