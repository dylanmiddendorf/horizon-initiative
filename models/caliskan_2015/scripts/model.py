import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

df = pd.read_csv('layout_features.csv')
X, y = df.drop('author', axis=1), df['author']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.1, shuffle=True)
clf = RandomForestClassifier(30)
clf.fit(X_train, y_train)
print(X_train)
res = clf.predict(X_test)
print(res, y_test)
print(accuracy_score(y_test, res))