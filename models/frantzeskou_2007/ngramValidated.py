import os
import random
from collections import defaultdict, Counter
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

# Attribute the authorship of unknown_code using SCAP with SPI.
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

# Function to split the files into training and testing sets
def split_files_across_authors(file_paths, train_proportion=0.80):
    author_files = defaultdict(list)
    
    # Group the files by author
    for file_path in file_paths:
        basename = os.path.basename(file_path)
        try:
            author, attempt_id_with_ext = basename.split('$')
            attempt_id, extension = attempt_id_with_ext.split('.')
            author_files[author].append(file_path)
        except ValueError:
            print(f"Filename format error: {basename}")
    
    # Split the files into training and testing sets
    train_files = defaultdict(list)
    test_files = defaultdict(list)
    
    for author, files in author_files.items():
        random.shuffle(files)
        split_index = int(len(files) * train_proportion)
        train_files[author] = files[:split_index]
        test_files[author] = files[split_index:]
        assert len(set(train_files[author]) & set(test_files[author])) == 0, f"Overlap found for author {author}"

    return train_files, test_files


# Main execution
if __name__ == "__main__":
    # Set source code directory and get a list of all file paths in the directory
    source_code_dir = ''
    file_paths = [os.path.join(source_code_dir, f) for f in os.listdir(source_code_dir)]
    
    # Split the files across training and testing
    train_files, test_files = split_files_across_authors(file_paths, train_proportion=0.80)
    
    # Define fixed n and L values for cross-validation
    n = 30  # n-gram size
    L = 6000  # top n-grams
    
    # Perform k-fold cross-validation on the files (not authors)
    k_folds = 5
    kf = KFold(n_splits=k_folds, shuffle=True, random_state=42)
    
    total_accuracy = 0

    # Perform k-fold cross-validation
    for train_indices, test_indices in kf.split(file_paths):
        # Split files into training and testing sets
        train_set = [file_paths[i] for i in train_indices]
        test_set = [file_paths[i] for i in test_indices]
        
        # Group the files by author for the training and testing sets
        train_files = defaultdict(list)
        test_files = defaultdict(list)
        
        for file_path in train_set:
            author, attempt_id_with_ext = os.path.basename(file_path).split('$')
            train_files[author].append(file_path)
            
        for file_path in test_set:
            author, attempt_id_with_ext = os.path.basename(file_path).split('$')
            test_files[author].append(file_path)

        # Generate author profiles from the training set
        author_profiles = get_author_profiles(train_files, n)
        
        # Calculate accuracy using the testing set
        accuracy = calculate_accuracy(author_profiles, test_files, n, L, scapRD)
        total_accuracy += accuracy
    
    # Compute and print the average accuracy across all folds
    avg_accuracy = total_accuracy / k_folds
    print(f"Average accuracy across {k_folds}-fold cross-validation: {avg_accuracy:.4f}")
