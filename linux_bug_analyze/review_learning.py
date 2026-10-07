"""ASReview model adapter. No LLM calls, pseudo labels, or pickle loading."""
from importlib.metadata import version
import random


class ReviewRanker:
    def __init__(self, seed=42):
        self.seed = seed
        self.hashes = None
        self.matrix = None

    def fit_predict(self, records, labels):
        from asreview.models.classifiers import Logistic
        from asreview.models.feature_extractors import Tfidf
        import pandas as pd

        train = {h: int(row['label'] == 'related') for h, row in labels.items()
                 if row['label'] in ('related', 'unrelated')}
        if set(train.values()) != {0, 1}:
            raise ValueError('至少需要一个人工相关例和一个不相关例才能学习；不确定不参与训练。')
        hashes = [r['hash'] for r in records]
        if self.hashes != hashes:
            # Use the same material for all records; on-demand UI patches must not
            # change the feature space halfway through the experiment.
            texts = pd.DataFrame({'title': [r['subject'] for r in records],
                                  'abstract': [r['body'] + '\n' + r['files'] for r in records]})
            vectorizer = Tfidf(ngram_range=(1, 2), min_df=1, max_df=1.0,
                               max_features=100_000, sublinear_tf=True)
            self.matrix = vectorizer.fit_transform(texts)
            self.hashes = hashes
        indices = [i for i, h in enumerate(hashes) if h in train]
        model = Logistic(class_weight='balanced', random_state=self.seed, max_iter=1000)
        model.fit(self.matrix[indices], [train[hashes[i]] for i in indices])
        positive_column = list(model.classes_).index(1)
        scores = model.predict_proba(self.matrix)[:, positive_column]
        return dict(zip(hashes, map(float, scores))), {
            'engine': 'ASReview Tfidf + Logistic', 'asreview_version': version('asreview'),
            'sklearn_version': version('scikit-learn'), 'seed': self.seed,
            'features': 'subject + body + changed paths; no diff; max_features=100000; ngram=(1,2)',
            'class_weight': 'balanced', 'training_labels': train,
            'warning': 'Uncalibrated relevance scores, not accuracy probabilities.',
        }


def choose_next(records, labels, seed, exploration_every):
    unseen = [r for r in records if r['hash'] not in labels]
    if not unseen:
        return None
    trained = {r['label'] for r in labels.values()} >= {'related', 'unrelated'}
    if not trained or len(labels) % exploration_every == 0:
        return random.Random(seed + len(labels)).choice(unseen)['hash']
    return max(unseen, key=lambda r: (r['score'] if r['score'] is not None else -1, r['hash']))['hash']


def score_stratified_sample(records, size, seed):
    """Equal samples across five score bands; threshold exploration, NOT a test set."""
    ordered = sorted(records, key=lambda r: (r['score'], r['hash']))
    rng = random.Random(seed)
    bands = [ordered[i * len(ordered) // 5:(i + 1) * len(ordered) // 5] for i in range(5)]
    for band in bands:
        rng.shuffle(band)
    result = []
    while len(result) < min(size, len(ordered)):
        for band in bands:
            if band and len(result) < size:
                result.append(band.pop()['hash'])
    return result
