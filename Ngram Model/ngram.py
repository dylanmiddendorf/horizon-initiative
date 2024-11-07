import ngram
import collections
import pandas as pd
from collections import defaultdict, Counter
import os
import random
import numpy as np
from sklearn.model_selection import KFold


# Generate byte-level n-grams from a string of source code.
def get_ngrams(s, n):
    s_bytes = s.encode()
    byte_ngrams = [s_bytes[i:i+n] for i in range(len(s_bytes) - n + 1)]
    return byte_ngrams


# Get the n-gram profiles for each author from their training files.
def get_author_profiles(author_files, n):
    author_profiles = {}
    for author, files in author_files.items():
        author_code = ''
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    author_code += f.read()
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

        ngrams = get_ngrams(author_code, n)
        ngram_freqs = Counter(ngrams)
        author_profiles[author] = ngram_freqs
    return author_profiles


# Attribute the authorship of unknown_code using SCAP.
def scapSPI(author_profiles, unknown_code, n, L):
    unknown_ngrams = get_ngrams(unknown_code, n)
    unknown_profile = Counter(unknown_ngrams)
    unknown_profile = Counter(dict(unknown_profile.most_common(L)))

    intersections = {}
    for author, profile in author_profiles.items():
        profile = Counter(dict(profile.most_common(L)))
        common_ngrams = set(profile.keys()) & set(unknown_profile.keys())
        intersections[author] = sum(profile[ngram] for ngram in common_ngrams)

    attributed_author = max(intersections, key=intersections.get)
    return attributed_author


# Attribute the authorship of unknown_code using SCAP with relative distance.
def scapRD(author_profiles, unknown_code, n, L):
    unknown_ngrams = get_ngrams(unknown_code, n)
    unknown_profile = Counter(unknown_ngrams)
    unknown_profile = Counter(dict(unknown_profile.most_common(L)))

    relative_distances = {}
    for author, profile in author_profiles.items():
        profile = Counter(dict(profile.most_common(L)))
        common_ngrams = set(profile.keys()) & set(unknown_profile.keys())
        all_ngrams = set(profile.keys()) | set(unknown_profile.keys())
        relative_distance = 1 - sum(min(profile[ngram], unknown_profile[ngram]) for ngram in common_ngrams) / sum(
            max(profile[ngram], unknown_profile.get(ngram, 0)) for ngram in all_ngrams
        )
        relative_distances[author] = relative_distance

    attributed_author = min(relative_distances, key=relative_distances.get)
    return attributed_author


# Calculate accuracy
def calculate_accuracy(author_profiles, test_files, n, L, method):
    total_predictions = 0
    correct_predictions = 0

    for true_author, files in test_files.items():
        for file_path in files:
            with open(file_path, 'r') as f:
                unknown_code = f.read()

            attributed_author = method(author_profiles, unknown_code, n, L)
            total_predictions += 1
            if attributed_author == true_author:
                correct_predictions += 1

    return correct_predictions / total_predictions if total_predictions > 0 else 0


# Function to perform hyperparameter tuning and cross-validation
def tune_hyperparameters(author_files, n_values, L_values, train_proportion=0.80, k_folds=5, enable_tuning=True):
    if not enable_tuning:
        print("Hyperparameter tuning is turned off.")
        return None, None  # Skip tuning if the flag is False

    # Prepare the folds for cross-validation
    all_authors = list(author_files.keys())
    kf = KFold(n_splits=k_folds, shuffle=True, random_state=42)

    best_accuracy = 0
    best_n = None
    best_L = None

    # Try different n and L values
    for n in n_values:
        for L in L_values:
            total_accuracy = 0
            print(f"Testing n={n}, L={L}")

            # Perform k-fold cross-validation
            for train_indices, test_indices in kf.split(all_authors):
                # Split authors into training and testing sets
                train_authors = [all_authors[i] for i in train_indices]
                test_authors = [all_authors[i] for i in test_indices]

                # Prepare training and testing file sets
                train_files = {author: author_files[author] for author in train_authors}
                test_files = {author: author_files[author] for author in test_authors}

                # Generate author profiles using training set
                author_profiles = get_author_profiles(train_files, n)

                # Calculate accuracy using the testing set and the chosen method (SCAP with relative distance)
                accuracy = calculate_accuracy(author_profiles, test_files, n, L, scapRD)
                total_accuracy += accuracy

            # Compute the average accuracy for this combination of n and L
            avg_accuracy = total_accuracy / k_folds
            print(f"Average accuracy for n={n}, L={L}: {avg_accuracy:.4f}")

            # Update the best n, L combination if needed
            if avg_accuracy > best_accuracy:
                best_accuracy = avg_accuracy
                best_n = n
                best_L = L

    # Output the best combination of n and L
    print(f"Best hyperparameters found: n={best_n}, L={best_L} with accuracy {best_accuracy:.4f}")
    return best_n, best_L


# Main execution
if __name__ == "__main__":
    # Set source code directory and get a list of all file paths in the directory
    source_code_dir = 'Datasets/1000Authors'
    file_paths = [os.path.join(source_code_dir, f) for f in os.listdir(source_code_dir)]

    # Dictionaries to hold file paths for training and testing
    train_files = defaultdict(list)
    test_files = defaultdict(list)

    train_proportion = 0.80

    # Group the files by author
    author_files = defaultdict(list)
    for file_path in file_paths:
        basename = os.path.basename(file_path)
        try:
            author, attempt_id_with_ext = basename.split('$')
            attempt_id, extension = attempt_id_with_ext.split('.')
            author_files[author].append(file_path)
        except ValueError:
            print(f"Filename format error: {basename}")

    # Split the files into training and testing sets
    for author, files in author_files.items():
        random.shuffle(files)
        split_index = int(len(files) * train_proportion)
        train_files[author] = files[:split_index]
        test_files[author] = files[split_index:]
        assert len(set(train_files[author]) & set(test_files[author])) == 0, f"Overlap found for author {author}"

    # Set n and L value ranges to tune
    n_values = [10, 15, 20, 25, 30]  # Possible n-gram sizes
    L_values = [4000, 5000, 6000]  # Possible top n-grams

    # Toggle hyperparameter tuning on or off
    enable_tuning = False

    # Call the tuning function (skip if tuning is off)
    if enable_tuning:
        best_n, best_L = tune_hyperparameters(author_files, n_values, L_values, enable_tuning=enable_tuning)
    else:
        best_n, best_L = 30, 6000   # Set your fixed values if tuning is off

    # Once the best n and L are found, you can use them to train and test with the full dataset
    if best_n is not None and best_L is not None:
        print(f"Final model will use n={best_n} and L={best_L}")

        # Generate author profiles with chosen n and L
        author_profiles = get_author_profiles(train_files, best_n)

        # Calculate and print the accuracy using the fixed hyperparameters
        accuracy = calculate_accuracy(author_profiles, test_files, best_n, best_L, scapRD)
        print(f"Accuracy with fixed parameters (n={best_n}, L={best_L}): {accuracy:.4f} for {source_code_dir}")
