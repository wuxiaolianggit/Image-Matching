import os
import pickle
import random

from tqdm import tqdm

from config import IMG_DIR, pickle_file, num_tests


def get_data():
    samples = []
    dirs = [d for d in os.listdir(IMG_DIR) if os.path.isdir(os.path.join(IMG_DIR, d))]
    for d in tqdm(dirs):
        build_vocab(d)

        dir = os.path.join(IMG_DIR, d)
        files = [f for f in os.listdir(dir) if f.endswith('.jpg')]

        for f in files:
            img_path = os.path.join(dir, f)
            img_path = img_path.replace('\\', '/')
            samples.append({'img': img_path, 'label': VOCAB[d]})

    return samples


def build_vocab(token):
    global VOCAB, IVOCAB
    if not token in VOCAB:
        next_index = len(VOCAB)
        VOCAB[token] = next_index
        IVOCAB[next_index] = token


def pick_one_file(folder):
    files = [f for f in os.listdir(folder) if f.endswith('.jpg')]
    file = random.choice(files)
    file = os.path.join(folder, file)
    return file


if __name__ == "__main__":
    VOCAB = {}
    IVOCAB = {}

    num_tests
    num_same = int(num_tests / 2)
    num_not_same = num_tests - num_same

    samples = get_data()
    with open(pickle_file, 'wb') as file:
        pickle.dump(samples, file)

    print(len(samples))
    print(samples[:10])

    out_lines = []

    picked = set()
    for _ in tqdm(range(num_same)):
        dirs = [d for d in os.listdir(IMG_DIR) if os.path.isdir(os.path.join(IMG_DIR, d))]
        folder = random.choice(dirs)
        while len([f for f in os.listdir(os.path.join(IMG_DIR, folder)) if f.endswith('.jpg')]) < 2:
            folder = random.choice(dirs)

        folder = os.path.join(IMG_DIR, folder)
        files = [f for f in os.listdir(folder) if f.endswith('.jpg')]
        files = random.sample(files, 2)
        out_lines.append('{} {} {}\n'.format(os.path.join(folder, files[0]), os.path.join(folder, files[1]), 1))

    for _ in tqdm(range(num_not_same)):
        dirs = [d for d in os.listdir(IMG_DIR) if os.path.isdir(os.path.join(IMG_DIR, d))]
        folders = random.sample(dirs, 2)
        while len([f for f in os.listdir(os.path.join(IMG_DIR, folders[0])) if f.endswith('.jpg')]) < 1 or len(
                [f for f in os.listdir(os.path.join(IMG_DIR, folders[1])) if f.endswith('.jpg')]) < 1:
            folders = random.sample(dirs, 2)

        file_0 = pick_one_file(os.path.join(IMG_DIR, folders[0]))
        file_1 = pick_one_file(os.path.join(IMG_DIR, folders[1]))
        out_lines.append('{} {} {}\n'.format(file_0, file_1, 0))

    with open('data/test_pairs.txt', 'w') as file:
        file.writelines(out_lines)