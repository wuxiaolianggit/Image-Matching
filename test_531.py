import json
import math
import os
import pickle
import tarfile
import time

import cv2 as cv
import numpy as np
import scipy.stats
import torch
from PIL import Image
from matplotlib import pyplot as plt
from tqdm import tqdm

from config import device
from config import im_size
from data_gen import data_transforms

angles_file = 'data/angles.txt'
IMG_FOLDER = 'data/jinhai531'
pickle_file = 'data/jinhai531_features.pkl'
transformer = data_transforms['val']


def extract(filename):
    with tarfile.open(filename, 'r') as tar:
        tar.extractall('data')


def get_image(filename):
    img = cv.imread(filename)
    img = cv.resize(img, (im_size, im_size))
    img = img[..., ::-1]  # RGB
    img = Image.fromarray(img, 'RGB')  # RGB
    img = transformer(img)
    img = img.to(device)
    return img


def gen_features(model):
    data = []
    dir_list = [d for d in os.listdir(IMG_FOLDER) if os.path.isdir(os.path.join(IMG_FOLDER, d))]
    for dir in tqdm(dir_list):
        dir_path = os.path.join(IMG_FOLDER, dir)
        file_list = [f for f in os.listdir(dir_path) if f.lower().endswith('.jpg')]
        for file in file_list:
            fullpath = os.path.join(dir_path, file)
            is_sample = file == '0.jpg'
            data.append({'fullpath': fullpath, 'file': file, 'dir': dir, 'is_sample': is_sample})
    with open('data/jinhai531_file_list.json', 'w') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    file_count = len(data)

    batch_size = 128
    start = time.time()

    with torch.no_grad():
        for start_idx in tqdm(range(0, file_count, batch_size)):
            end_idx = min(file_count, start_idx + batch_size)
            length = end_idx - start_idx

            imgs = torch.zeros([length, 3, im_size, im_size], dtype=torch.float)
            for idx in range(0, length):
                i = start_idx + idx
                filepath = data[i]['fullpath']
                imgs[idx] = get_image(filepath)

            features = model(imgs.to(device)).cpu().numpy()
            for idx in range(0, length):
                i = start_idx + idx
                feature = features[idx]
                data[i]['feature'] = feature

    elapsed_time = time.time() - start
    print('elapsed time(sec) per image: {}'.format(elapsed_time / file_count))

    with open(pickle_file, 'wb') as file:
        pickle.dump(data, file)


def evaluate(model):
    model.eval()
    with open(pickle_file, 'rb') as file:
        data = pickle.load(file)

    angles = []

    samples = [f for f in data if f['is_sample']]
    photos = [f for f in data if not f['is_sample']]

    with torch.no_grad():
        for sample in tqdm(samples):
            feature0 = sample['feature']
            x0 = feature0 / np.linalg.norm(feature0)
            ad_no_0 = sample['dir']
            for photo in photos:
                feature1 = photo['feature']
                x1 = feature1 / np.linalg.norm(feature1)
                ad_no_1 = photo['dir']
                cosine = np.dot(x0, x1)
                cosine = np.clip(cosine, -1, 1)
                theta = math.acos(cosine)
                theta = theta * 180 / math.pi

                is_same = int(ad_no_0 == ad_no_1)
                angles.append('{} {}\n'.format(theta, is_same))

    with open('data/angles.txt', 'w') as file:
        file.writelines(angles)


def get_threshold():
    # return 25.50393648495902
    with open(angles_file, 'r') as file:
        lines = file.readlines()

    data = []

    for line in lines:
        tokens = line.split()
        angle = float(tokens[0])
        type = int(tokens[1])
        data.append({'angle': angle, 'type': type})

    min_error = 6000
    min_threshold = 0

    for d in data:
        threshold = d['angle']
        type1 = len([s for s in data if s['angle'] <= threshold and s['type'] == 0])
        type2 = len([s for s in data if s['angle'] > threshold and s['type'] == 1])
        num_errors = type1 + type2
        if num_errors < min_error:
            min_error = num_errors
            min_threshold = threshold

    # print(min_error, min_threshold)
    return min_threshold


def accuracy(threshold):
    with open(angles_file) as file:
        lines = file.readlines()

    num_tests = len(lines)
    wrong = 0
    for line in lines:
        tokens = line.split()
        angle = float(tokens[0])
        type = int(tokens[1])
        if type == 1 and angle > threshold or type == 0 and angle <= threshold:
            wrong += 1

    accuracy = 1 - wrong / num_tests
    return accuracy


def visualize(threshold):
    with open(angles_file) as file:
        lines = file.readlines()

    ones = []
    zeros = []

    for line in lines:
        tokens = line.split()
        angle = float(tokens[0])
        type = int(tokens[1])
        if type == 1:
            ones.append(angle)
        else:
            zeros.append(angle)

    bins = np.linspace(0, 180, 181)

    plt.hist(zeros, bins, density=True, alpha=0.5, label='0', facecolor='red')
    plt.hist(ones, bins, density=True, alpha=0.5, label='1', facecolor='blue')

    mu_0 = np.mean(zeros)
    sigma_0 = np.std(zeros)
    y_0 = scipy.stats.norm.pdf(bins, mu_0, sigma_0)
    plt.plot(bins, y_0, 'r--')
    mu_1 = np.mean(ones)
    sigma_1 = np.std(ones)
    y_1 = scipy.stats.norm.pdf(bins, mu_1, sigma_1)
    plt.plot(bins, y_1, 'b--')
    plt.xlabel('theta')
    plt.ylabel('theta j Distribution')
    plt.title(
        r'Histogram : mu_0={:.4f},sigma_0={:.4f}, mu_1={:.4f},sigma_1={:.4f}'.format(mu_0, sigma_0, mu_1, sigma_1))

    plt.legend(loc='upper right')
    plt.plot([threshold, threshold], [0, 0.05], 'k-', lw=2)
    plt.savefig('images/theta_dist.png')
    plt.show()


def test(model):
    print('Generating features...')
    gen_features(model)

    print('Evaluating {}...'.format(angles_file))
    # evaluate(model)

    print('Calculating threshold...')
    # threshold = 70.36
    thres = get_threshold()
    print('Calculating accuracy...')
    acc = accuracy(thres)
    print('Accuracy: {}%, threshold: {}'.format(acc * 100, thres))
    return acc, thres


if __name__ == "__main__":
    if not os.path.isdir('data/jinhai531'):
        extract('data/jinhai_531.tar.gz')

    checkpoint = 'BEST_checkpoint.tar'
    checkpoint = torch.load(checkpoint)
    model = checkpoint['model']
    model = model.to(device)
    model.eval()

    acc, threshold = test(model)

    print('Visualizing {}...'.format(angles_file))
    visualize(threshold)
    #
    # print('error analysis...')
    # error_analysis(threshold)