from __future__ import absolute_import, division, print_function, unicode_literals
import tensorflow as tf
import time
import json
from prediction_hibert_model import *

BUFFER_SIZE = 20000
BATCH_SIZE = 32
MIN_LENGTH = 5
EPOCHS = 20
DATA = 'predict_train.json'
directory = "data/encoded/"
checkpoint_path = "./checkpoints/predict_train"
num_layers = 6
d_model = 512
dff = 512
num_heads = 8
seq_length = 20
para_length = 10
dropout_rate = 0.1

def write(meg):
    with open("predict_out.txt", "a") as fp:
    	fp.write(meg+"\n")

def readData(filename):
    train_dataset = []
    with open(directory + filename, 'r') as fp:
        obj = json.load(fp)
        batch = []
        for i in range(len(obj)):
            batch.append(obj[i])
            if (len(batch) == BATCH_SIZE):
                train_dataset.append((int(i/BATCH_SIZE), batch))
                batch = []
    return train_dataset

def train_step(sample_transformer, loss_object, optimizer, train_loss, train_accuracy, inp, tar, masked_index):
    tar_inp = tar[:, :-1]
    tar_real = tar[:, 1:]
        
    with tf.GradientTape() as tape:
        predictions, _ = sample_transformer(inp, tar_inp, masked_index, True)
        loss = loss_function(loss_object, tar_real, predictions)
    
    gradients = tape.gradient(loss, sample_transformer.trainable_variables)    
    optimizer.apply_gradients(zip(gradients, sample_transformer.trainable_variables))
    
    train_loss(loss)
    train_accuracy(tar_real, predictions)

def main():
    write("start loading data...")
    vocab_size = getVocab() 
    input_vocab_size = vocab_size
    target_vocab_size = vocab_size
    train_dataset =  readData(DATA)
    write("data loaded.")

    config = tf.ConfigProto(log_device_placement=True, allow_soft_placement=True)
    config.gpu_options.allow_growth = True
    tf.enable_eager_execution(config=config)
    sample_transformer = PredictionHibert(num_layers, d_model, num_heads, dff,
                          input_vocab_size, target_vocab_size, dropout_rate)    
    learning_rate = CustomSchedule(d_model)
    optimizer = tf.keras.optimizers.Adam(learning_rate, beta_1=0.9, beta_2=0.98, epsilon=1e-9)
    loss_object = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True, reduction='none')
    train_loss = tf.keras.metrics.Mean(name='train_loss')
    train_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name='train_accuracy')
    ckpt_manager = getCheckpoint(sample_transformer, optimizer, checkpoint_path)
    write("checkpoint checked.")

    write("start training...")
    for epoch in range(EPOCHS):
        write("training epoch " + str(epoch))
        start = time.time()
        train_loss.reset_states()
        train_accuracy.reset_states()
        for (batch, inp) in train_dataset:
            masked_inp_batch, masked_sentence_batch, masked_index_batch = maskBatch(inp, para_length, seq_length)        
            train_step(sample_transformer, loss_object, optimizer, train_loss, train_accuracy, 
                masked_inp_batch, masked_sentence_batch, masked_index_batch)
            if batch % 5 == 0:
                write('Epoch {} Batch {} Loss {:.4f} Accuracy {:.4f}'.format(
                    epoch + 1, batch, train_loss.result(), train_accuracy.result()))
            if batch % 20 == 0:
                ckpt_save_path = ckpt_manager.save()
                write('Saving checkpoint for epoch {} at {}'.format(epoch+1, ckpt_save_path))
       
        ckpt_save_path = ckpt_manager.save()
        write('Saving checkpoint for epoch {} at {}'.format(epoch+1, ckpt_save_path))
    
        write('Epoch {} Loss {:.4f} Accuracy {:.4f}'.format(epoch + 1, 
                                                train_loss.result(), 
                                                train_accuracy.result()))
    
        write('Time taken for 1 epoch: {} secs\n'.format(time.time() - start))

main()
