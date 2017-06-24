import os
import sys
import time
import numpy as np
import tensorflow as tf

from scipy.misc import imread, imresize
from model import CRNN

# Constants
CHAR_VECTOR = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ\\|:_-+=!@#$%?&*()"\' '
NUM_CLASSES = len(CHAR_VECTOR)

def resize_image(image):
    final_arr = np.zeros((32, 400))
    im_arr = imread(image, mode='L')
    r, c = np.shape(im_arr)
    ratio = float(32 / r)
    im_arr_resized = imresize(im_arr, (32, int(c * ratio)))
    final_arr[:, 0:np.shape(im_arr_resized)[1]] = im_arr_resized
    return final_arr

def create_ground_truth(label):
    """
        Create our ground truth by replacing each char by its index in the CHAR_VECTOR
    """
    return [CHAR_VECTOR.index(l) for l in label.split('_')[1]]

def ground_truth_to_word(ground_truth):
    """
        Return the word string based on the input ground_truth
    """
    return ''.join([CHAR_VECTOR[i] for i in ground_truth])

def load_data(folder):
    examples = []

    count = 0
    for f in os.listdir(folder):        
        if count > 100:
            break
        examples.append(
            (
                resize_image(
                    os.path.join(folder, f)
                ),
                create_ground_truth(
                    f
                ),
                len(f.split('_')[1])
            )
        )
        print(examples[-1][1])
        count += 1
    return examples

def main(args):
    """
        Usage: run.py [iteration_count] [batch_size] [data_dir] [log_save_dir] [graph_save_dir]
    """

    # The user-defined training parameters
    iteration_count = int(args[1])
    batch_size = int(args[2])
    data_dir = args[3]
    log_save_dir = args[4]
    graph_save_dir = args[5]

    # The training data
    data = load_data(data_dir)
    train_data = data[0:int(len(data) * 0.70)]
    test_data = data[int(len(data) * 0.70):]

    graph = tf.Graph()

    with graph.as_default():
        inputs = tf.placeholder(tf.float32, [None, 32, 400])
        
        # The CRNN
        crnn = CRNN(inputs, batch_size)

        # Our target output
        targets = tf.sparse_placeholder(tf.int32, name='targets')

        # The length of the sequence
        seq_len = tf.placeholder(tf.int32, [None], name='seq_len')

        logits = tf.reshape(crnn, [batch_size, -1, 50])

        # Final layer, the output of the BLSTM
        logits = tf.transpose(logits, (1, 0, 2))

        # Loss and cost calculation
        loss = tf.nn.ctc_loss(targets, logits, seq_len)
        cost = tf.reduce_mean(loss)

        # Training step
        optimizer = tf.train.MomentumOptimizer(0.01, 0.9).minimize(cost)

        # The decoded answer
        decoded, log_prob = tf.nn.ctc_greedy_decoder(logits, seq_len)

        # The error rate
        acc = tf.reduce_mean(tf.edit_distance(tf.cast(decoded[0], tf.int32), targets))

    with tf.Session(graph=graph) as sess:
        tf.global_variables_initializer().run()

        # Train
        
        print(len(train_data))

        for it in range(0, iteration_count):
            iter_avg_cost = 0
            start = time.time()
            for b in [train_data[x*batch_size:x*batch_size + batch_size] for x in range(0, int(len(train_data) / batch_size))]:
                data, labels, seq_lens = zip(*b)
                print(len(data))
                print(len(labels))
                print(len(seq_lens))
                cost = sess.run(
                    ['cost'],
                    {
                        inputs: data,
                        targets: (np.array([x for i in range(0, seq_len)], dtype=np.int64), labels),
                        seq_len: list(seq_lens)
                    }
                )
                iter_avg_cost += cost / batch_size

            print('[{}] {} : {}'.format(time.time() - start, it, iter_avg_cost))

        # Test
        data, labels, seq_lens = zip(*test_data)
        decoded, cost = sess.run(
            ['decoded', 'cost'],
            {
                inputs: data,
                targets: labels,
                seq_len: list(seq_lens),
            }
        )
        print('Result: {} / {} correctly read'.format(len(filter(zip(decoded, labels))), len(decoded)))

if __name__=='__main__':
    main(sys.argv)