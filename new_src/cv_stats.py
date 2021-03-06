import os
import numpy as np
import pandas as pd
from scipy import interp
import matplotlib.pyplot as plt


parent_dir = os.path.dirname(os.getcwd())
test_logs_dir = os.path.join(parent_dir, "test_logs_2")
data_dir = os.path.join(parent_dir, "models_2", "t1ce_pyramid_adagrade_17")

subject_dirs = os.listdir(test_logs_dir)
metrics_paths, roc_curves = [], []
for subject_dir in subject_dirs:
    metrics_paths.append(os.path.join(test_logs_dir, subject_dir, "metrics.csv"))
    roc_curves.append(np.load(os.path.join(test_logs_dir, subject_dir, "roc_curve.npy")))

df = pd.concat(map(pd.read_csv, metrics_paths))

acc = df["acc"].values
hgg_acc = df["hgg_acc"].values
lgg_acc = df["lgg_acc"].values

loss = df["loss"].values
hgg_loss = df["hgg_loss"].values
lgg_loss = df["lgg_loss"].values

hgg_precision = df["hgg_precision"].values
lgg_precision = df["lgg_precision"].values
hgg_recall = df["hgg_recall"].values
lgg_recall = df["lgg_recall"].values
roc_score = df["roc_auc"].values

accs = [acc, hgg_acc, lgg_acc]
losses = [loss, hgg_loss, lgg_loss]
metrics = [hgg_precision, hgg_recall,
           lgg_precision, lgg_recall, roc_score]

# Boxplot of accuracy
plt.figure(num="Accuracy")
plt.title("Prediction Accuracy for Different Data", fontsize=14)
plt.boxplot(accs, 0, "k.", labels=["Total", "HGG", "LGG"], showmeans=True)
plt.grid("on", linestyle="--", linewidth=0.5, alpha=0.3)
axes = plt.gca()
axes.set_ylim([0.5, 1.02])
plt.legend()
plt.ylabel("Accuracy", fontsize=14)
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)

# Boxplot of loss
plt.figure(num="Loss")
plt.title("Prediction Cross Entropy for Different Data", fontsize=14)
plt.boxplot(losses, 0, "k.", labels=["Total", "HGG", "LGG"], showmeans=True)
plt.grid("on", linestyle="--", linewidth=0.5, alpha=0.3)
axes = plt.gca()
axes.set_ylim([0, 1])
plt.ylabel("Cross Entropy", fontsize=14)
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)

# Boxplot for precision and recall
plt.figure(num="Other Metrics of Predictions")
plt.title("Precision and Recall for HGG and LGG", fontsize=14)
plt.boxplot(metrics, 0, "k.", labels=["HGG\nPrecision", "HGG\nRecall",
                                      "LGG\nPrecision", "LGG\nRecall",
                                      "ROC\nAccuracy"], showmeans=True)
plt.grid("on", linestyle="--", linewidth=0.5, alpha=0.3)
axes = plt.gca()
axes.set_ylim([0.5, 1.02])
plt.ylabel("Metrics Accuracy", fontsize=14)
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)

# ROC Curves
tprs = []
mean_fpr = np.linspace(0, 1, 100)

plt.figure(num="ROC Curves of Predictions")
for curve in roc_curves[:-1]:
    tprs.append(interp(mean_fpr, curve[0], curve[1]))
    tprs[-1][0] = 0.0
    plt.plot(curve[0], curve[1], color="k", lw=1, alpha=0.2)
plt.plot(roc_curves[-1][0], roc_curves[-1][1], color="k", lw=1, alpha=0.2,
         label="ROC Curves of {} Predictions".format(len(roc_curves)))
plt.plot([0, 1], [0, 1], linestyle="--", color="gray", lw=0.8, alpha=0.5)

mean_tpr = np.mean(tprs, axis=0)
mean_tpr[-1] = 1.0
mean_auc = np.mean(roc_score)
std_auc = np.std(roc_score)

plt.plot(mean_fpr, mean_tpr, color="coral",
         label="Mean ROC (AUC = {0:.2f} $\pm$ {1:.2f})".format(mean_auc, std_auc),
         lw=2, alpha=.8)

std_tpr = np.std(tprs, axis=0)
tprs_upper = np.minimum(mean_tpr + std_tpr, 1)
tprs_lower = np.maximum(mean_tpr - std_tpr, 0)
plt.fill_between(mean_fpr, tprs_lower, tprs_upper, color='grey', alpha=0.5,
                 label="$\pm$ 1 standard deviation")
plt.grid("on", linestyle="--", linewidth=0.5, alpha=0.3)
plt.xlabel("False Positive Rate", fontsize=14)
plt.ylabel("True Positive Rate", fontsize=14)
plt.title("ROC Curves of All Predictions", fontsize=14)
plt.xticks(fontsize=12)
plt.yticks(fontsize=12)
plt.legend(fontsize=12)
plt.show()

# Learning Curve

# data_dir = os.path.join(parent_dir, "models_1", "t1ce_pyramid_adam_17")

acc, loss = [], []
val_acc, val_loss = [], []
kfolds = ["kfold0", "kfold1", "kfold2", "kfold3"]

for kfold in kfolds:
    kfold_dir = os.path.join(data_dir, kfold)
    data_path = os.path.join(kfold_dir, "learning_curv.csv")
    pdf = pd.read_csv(data_path, sep=";")
    acc.append(pdf["acc"].values)
    loss.append(pdf["loss"].values)
    val_acc.append(pdf["val_acc"].values)
    val_loss.append(pdf["val_loss"].values)

epoch_num = len(acc[0])
x = np.arange(epoch_num)


def plot_metric(data, kfolds, window_name, ylabel, title, loc=1):
    x = np.arange(len(data[0]))
    plt.figure(num=window_name)
    for i in range(len(kfolds)):
        plt.plot(x, data[i], label=kfolds[i], alpha=0.7)
    plt.grid("on", linestyle="--", linewidth=0.5, alpha=0.3)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.legend(fontsize=12, loc=loc)
    plt.xlabel("Epoches", fontsize=14)
    plt.ylabel(ylabel, fontsize=14)
    plt.title(title, fontsize=14)
    plt.show()
    return


plot_metric(acc, kfolds, "Training Accuracy", "Accuracy", "Training Accuracy of Four Folds", 4)
plot_metric(loss, kfolds, "Training Loss", "Loss", "Training Loss of Four Folds", 1)
plot_metric(val_acc, kfolds, "Validation Accuracy", "Accuracy", "Validation Accuracy of Four Folds", 4)
plot_metric(val_loss, kfolds, "Validation Loss", "Loss", "Validation Loss of Four Folds", 1)


# Confusion Matrix

pnum = 42
nnum = 15

tn = np.array(df["TN"].values) / nnum
fp = np.array(df["FP"].values) / nnum
fn = np.array(df["FN"].values) / pnum
tp = np.array(df["TP"].values) / pnum


print("True Negative: {0:.3f} +/- {1:.3f}".format(np.mean(tn), np.std(tn)))
print("False Positive: {0:.3f} +/- {1:.3f}".format(np.mean(fp), np.std(fp)))
print("False Negative: {0:.3f} +/- {1:.3f}".format(np.mean(fn), np.std(fn)))
print("True Positive: {0:.3f} +/- {1:.3f}".format(np.mean(tp), np.std(tp)))
