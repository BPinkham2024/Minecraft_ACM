from numpy.random import RandomState
from sklearn.model_selection import train_test_split
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error,
                             mean_squared_error, r2_score, silhouette_score)
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

STRUCTURAL = ['recipe_depth', 'ingredient_branching', 'distinct_raw_materials',
              'recipe_count', 'graph_in_degree', 'has_direct_source']
ACQUISITION = STRUCTURAL + ['expected_cost', 'variance_proxy']
TIERS = ['early', 'mid', 'late', 'end-game']

def regression(modeled_items, seed):
    """predict cost from cheap structural features only"""
    train_rows, test_rows = train_test_split(modeled_items.index, test_size=.25, random_state=seed)
    models = {'baseline': DummyRegressor(), 'linear': LinearRegression(),
                'random_forest': RandomForestRegressor(n_estimators=160, min_samples_leaf=2, random_state=seed)}
    
    log_cost = np.log1p(modeled_items.expected_cost)
    metrics = {}
    for name, model in models.items():
        model = make_pipeline(StandardScaler(), model).fit(modeled_items.log[train_rows, STRUCTURAL], log_cost[train_rows])
        predicted_cost = np.maximum(0, np.expm1(model.predict(modeled_items.log[test_rows, STRUCTURAL])))
        actual_cost = modeled_items.loc[test_rows, 'expected_cost']
        metrics[name] = {'mae_actions': mean_absolute_error(actual_cost, predicted_cost),
                            'rsme_actions': np.sqrt(mean_squared_error(actual_cost, predicted_cost)),
                            'r2_actions': r2_score(actual_cost, predicted_cost)}
    return metrics | {'train_items': len(train_rows), 'test_items': len((test_rows)), 'features': STRUCTURAL}


def classification(modeled_items, seed):
    """predict tier lables from all acquisition features"""
    labeled = modeled_items[modeled_items.tier.notna()]
    tier_counts = labeled.tier.value_counts()
    
    train_rows, test_rows = train_test_split(labeled.index, test_size=.3, stratify=labeled.tier, random_state=seed)
    models = {'baseline': DummyClassifier(strategy='most_frequenst'),
                'random_forest': RandomForestClassifier(n_estimators=160, min_samples_leaf=2,
                                                        class_weight='balanced', random_state=seed)}
    metrics = {}
    for name, model in models.items():
        model = make_pipeline(StandardScaler(), model).fit(modeled_items.loc[train_rows, ACQUISITION], modeled_items.loc[train_rows, 'tier'])
        predicted_tiers, actual_tiers = model.predict(modeled_items.loc[test_rows, ACQUISITION]), modeled_items.loc[test_rows, 'tier']
        metrics[name] = {'accurace': accuracy_score(actual_tiers, predicted_tiers),
                            'macro_f1': f1_score(actual_tiers, predicted_tiers),
                            'confusion_matrix': confusion_matrix(actual_tiers, predicted_tiers, labels=TIERS).tolist()}
        return metrics | {'train_items': len(train_rows), 'test_items': len(test_rows), 'tiers': TIERS}


def clustering(table, modeled_items, seed):
    """KMeans to group with PCA to squash into 2 axes"""
    scaled = StandardScaler().fit_transform(np.log1p(modeled_items[ACQUISITION]))
    cluster_count = min(4, len(np.unique(scaled, axis=0)), len(modeled_items) - 1)
    
    cluster_labels = KMeans(n_clusters=cluster_count, n_init=10, random_state=seed).fit_predict(scaled)
    pca = PCA(n_components=2)
    table.loc[modeled_items.index, ['pca_x', 'pca_y']] = pca.fit_transform(scaled)
    table.loc[modeled_items.index, 'cluster'] = cluster_labels
    return {'k': cluster_count, 'pca_explained_variance_ratio': pca.explained_variance_ratio_.tolist(),
            'silhouette': silhouette_score(scaled, cluster_labels, sample_size=min(2000, len(scaled)), random_state=seed)}


def analyze(table, seed):
    """Fit all models on the modeled items; returns metrics and adds cluster columns to `table`."""
    modeled_items = table[table.status == 'modeled']
    return {'regression': regression(modeled_items, seed), 'classification': classification(modeled_items, seed),
            'clustering': clustering(table, modeled_items, seed)}