#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define LOG2(x) (log(x) / log(2))

// Function to calculate the entropy of a given class distribution
double calculate_entropy(int *class_count, int num_classes, int total_samples) {
  double entropy = 0.0;
  for (int i = 0; i < num_classes; ++i) {
    if (class_count[i] > 0) {
      double p = (double)class_count[i] / total_samples;
      entropy -= p * LOG2(p);
    }
  }
  return entropy;
}

// Function to calculate the information gain of a feature
double calculate_information_gain(float *feature, int *key, int num_samples,
                                  int num_classes) {
  // Calculate the entropy of the entire dataset (H(Y))
  int *class_count = (int *)calloc(num_classes, sizeof(int));
  for (int i = 0; i < num_samples; ++i) {
    class_count[key[i]]++;
  }
  double total_entropy =
      calculate_entropy(class_count, num_classes, num_samples);

  // Calculate the conditional entropy H(Y|X)
  double conditional_entropy = 0.0;
  // Using a simple split at the median for simplicity
  float median = feature[num_samples / 2];  // Assuming feature is sorted
  int *left_class_count = (int *)calloc(num_classes, sizeof(int));
  int *right_class_count = (int *)calloc(num_classes, sizeof(int));
  int left_count = 0, right_count = 0;

  for (int i = 0; i < num_samples; ++i) {
    if (feature[i] <= median) {
      left_class_count[key[i]]++;
      left_count++;
    } else {
      right_class_count[key[i]]++;
      right_count++;
    }
  }

  if (left_count > 0) {
    double left_entropy =
        calculate_entropy(left_class_count, num_classes, left_count);
    conditional_entropy += ((double)left_count / num_samples) * left_entropy;
  }
  if (right_count > 0) {
    double right_entropy =
        calculate_entropy(right_class_count, num_classes, right_count);
    conditional_entropy += ((double)right_count / num_samples) * right_entropy;
  }

  printf("left=%d right=%d\n", left_count, right_count);

  free(class_count);
  free(left_class_count);
  free(right_class_count);

  return total_entropy - conditional_entropy;
}

int main() {
  int num_samples = 6;     // Example number of samples
  int num_features = 3;    // Example number of features
  int num_classes = 2;     // Example number of classes
  double threshold = 0.1;  // Example threshold for information gain

  // Example data
  float features[6][3] = {{2.3, 4.5, 3.1}, {3.1, 2.2, 3.5}, {4.0, 3.3, 2.8},
                          {5.2, 3.1, 4.6}, {5.5, 1.5, 3.0}, {6, 2.9, 2.1}};
  int key[6] = {0, 0, 0, 1, 1, 1};

  // Check information gain for each feature
  for (int i = 0; i < num_features; ++i) {
    // Extract the feature column
    float *feature = (float *)malloc(num_samples * sizeof(float));
    for (int j = 0; j < num_samples; ++j) {
      feature[j] = features[j][i];
    }

    // Calculate the information gain
    double info_gain =
        calculate_information_gain(feature, key, num_samples, num_classes);
    printf("Information Gain for feature %d: %lf\n", i, info_gain);

    // Check if the information gain is below the threshold
    if (info_gain < threshold) {
      printf("Feature %d provides information gain below the threshold.\n", i);
    }

    free(feature);
  }

  return 0;
}
