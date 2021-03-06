#!/usr/bin/env python
# -*- coding: utf-8 -*-
#------------------------------------------------------
# @ File       : train.py
# @ Description:  
# @ Author     : Alex Chung
# @ Contact    : yonganzhong@outlook.com
# @ License    : Copyright (c) 2017-2018
# @ Time       : 2020/4/24 上午11:01
# @ Software   : PyCharm
#-------------------------------------------------------


import os
import numpy as np
from datetime import datetime
import tensorflow as tf
from VGG16_Tensorflow.nets.VGG16 import VGG16

from DataProcess.load_dataset import dataset_batch, get_samples

# dataset path
train_dir = '/home/alex/Documents/dataset/flower_split/train'
val_dir = '/home/alex/Documents/dataset/flower_split/val'

# pretrain model
model_dir = '/home/alex/Documents/pretrain_model/vgg16'
npy_model_path = os.path.join(model_dir, 'vgg16.npy')

# outputs path
save_dir = os.path.join('../', 'outputs', 'model', 'model.ckpt')
log_dir = os.path.join('../', 'outputs', 'logs')

input_shape = [224, 224, 3]
num_classes=5
batch_size=32
learning_rate=0.001
keep_prob = 0.8
epoch = 30
save_step_period = 2000  # set step period to save model

num_train_samples = get_samples(train_dir)
num_val_samples = get_samples(val_dir)

if __name__ == "__main__":

    # get total step of the number train epoch
    step_per_epoch = num_train_samples // batch_size  # get num step of per epoch
    max_step = epoch * step_per_epoch  # get total step of several epoch

    vgg = VGG16(input_shape, num_classes=num_classes, learning_rate=learning_rate)

    # add scalar value to summary protocol buffer
    tf.summary.scalar('loss', vgg.loss)
    tf.summary.scalar('accuracy', vgg.accuracy)

    train_image_batch, train_label_batch = \
        dataset_batch(data_dir=train_dir, batch_size=batch_size, epoch=epoch, is_training=True).get_next()

    val_image_batch, val_label_batch = \
        dataset_batch(data_dir=val_dir, batch_size=batch_size, epoch=epoch, is_training=False).get_next()

    # create saver
    saver = tf.train.Saver()
    init_op = tf.group(tf.global_variables_initializer(),
                       tf.local_variables_initializer())

    # os.environ["CUDA_VISIBLE_DEVICES"] = '0'
    config = tf.ConfigProto()
    # config.gpu_options.per_process_gpu_memory_fraction = 0.5  # maximun alloc gpu50% of MEM
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as sess:
        sess.run(init_op)

        graph = tf.get_default_graph()
        write = tf.summary.FileWriter(logdir=log_dir, graph=graph)

        model_variable = tf.global_variables()
        for var in model_variable:
            print(var.name, var.op.name)
            print(var.shape)
        # load weight
        # get and add histogram to summary protocol buffer
        logit_weight = graph.get_tensor_by_name(name='vgg16/fc8/Weight:0')
        tf.summary.histogram(name='logits/Weights', values=logit_weight)
        logit_biases = graph.get_tensor_by_name(name='vgg16/fc8/Bias:0')
        tf.summary.histogram(name='logits/Biases', values=logit_biases)
        # merges all summaries collected in the default graph
        summary_op = tf.summary.merge_all()

        vgg.load_weights(sess, weight_file=npy_model_path, custom_variable=['fc8'])

        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(sess=sess, coord=coord)
        try:
            if not coord.should_stop():

                # ++++++++++++++++++++++++++++++++++start training+++++++++++++++++++++++++++++++++++++++++++++++++
                # used to record the number step of per epoch
                step_epoch = 0
                for step in range(max_step):
                    # --------------------------------print number of epoch--------------------------------------
                    if (step) % step_per_epoch == 0:
                        tmp_epoch = (step + 1) // step_per_epoch
                        print('Epoch: {0}/{1}'.format(tmp_epoch+1, epoch))

                    # +++++++++++++++++++++++++++++++train part++++++++++++++++++++++++++++++++++++++++++++++++
                    train_image, train_label = sess.run([train_image_batch, train_label_batch])

                    feed_dict = vgg.fill_feed_dict(image_feed=train_image, label_feed=train_label, keep_prob=keep_prob)

                    _, train_loss, train_accuracy, summary = sess.run(
                        fetches=[vgg.train, vgg.loss, vgg.accuracy, summary_op], feed_dict=feed_dict)
                    write.add_summary(summary=summary, global_step=step)

                    step_epoch += 1
                    print(
                        '\tstep {0}:loss value {1}  train accuracy {2}'.format(step_epoch, train_loss, train_accuracy))

                    # -------------------------save_model every per save_step_period--------------------------------
                    if (step + 1) % save_step_period == 0:
                        saver.save(sess, save_path=save_dir, global_step=vgg.global_step)

                    # ++++++++++++++++++++++++++++++++validation part++++++++++++++++++++++++++++++++++++++++++++
                    # execute validation when complete every epoch
                    # validation use with all validation dataset
                    if (step + 1) % step_per_epoch == 0:  # complete training of epoch
                        val_losses = []
                        val_accuracies = []
                        val_max_steps = int(num_val_samples / batch_size)
                        for _ in range(val_max_steps):
                            val_images, val_labels = sess.run([val_image_batch, val_label_batch])

                            feed_dict = vgg.fill_feed_dict(image_feed=val_images, label_feed=val_labels,
                                                           keep_prob=1.0)

                            val_loss, val_acc = sess.run([vgg.loss, vgg.accuracy], feed_dict=feed_dict)

                            val_losses.append(val_loss)
                            val_accuracies.append(val_acc)
                        mean_loss = np.array(val_losses, dtype=np.float32).mean()
                        mean_acc = np.array(val_accuracies, dtype=np.float32).mean()

                        print("\t{0}: epoch {1}  val Loss : {2}, val accuracy :  {3}".format(datetime.now(),
                                                                                             (step + 1) // step_per_epoch,
                                                                                             mean_loss, mean_acc))
                        step_epoch = 0  # update step_epoch
                saver.save(sess, save_path=save_dir, global_step=vgg.global_step)
                write.close()


        except Exception as e:
            print(e)
        coord.request_stop()
        coord.join(threads)
    sess.close()
    print('model training has complete')






