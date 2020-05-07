#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @ File VGG16_Train.py
# @ Description :
# @ Author alexchung
# @ Time 14/10/2019 PM 20:07

import os
import cv2 as cv
import matplotlib.pyplot as plt
from datetime import datetime
import tensorflow as tf
# from VGG16.VGG16 import VGG16
from VGG16_Tensorflow.nets.VGG16_slim import VGG16
import numpy as np
from DataProcess.read_TFRecord import dataset_tfrecord, get_num_samples
from tensorflow.python.framework import graph_util


original_dataset_dir = '/home/alex/Documents/dataset/flower_photos'
tfrecord_dir = os.path.join(original_dataset_dir, 'tfrecord')

train_data_path = os.path.join(tfrecord_dir, 'train')
test_data_path = os.path.join(tfrecord_dir, 'test')

model_path = os.path.join(os.getcwd(), 'model')
pretrain_model_dir = '/home/alex/Documents/pretraing_model/vgg16/vgg16.ckpt'
logs_dir = os.path.join(os.getcwd(), 'logs')


flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_integer('height', 224, 'Number of height size.')
flags.DEFINE_integer('width', 224, 'Number of width size.')
flags.DEFINE_integer('depth', 3, 'Number of depth size.')
flags.DEFINE_integer('num_classes', 5, 'Number of image class.')
flags.DEFINE_integer('batch_size', 32, 'Batch size Must divide evenly into the dataset sizes.')
flags.DEFINE_integer('epoch', 30, 'Number of epoch size.')
flags.DEFINE_float('learning_rate', 0.01, 'Initial learning rate.')
flags.DEFINE_float('decay_rate', 0.9, 'Number of learning decay rate.')
flags.DEFINE_integer('num_epoch_per_decay', 2, 'Number epoch after each leaning rate decapy.')
flags.DEFINE_float('keep_prop', 1.0, 'Number of probability that each element is kept.')
flags.DEFINE_float('weight_decay', 0.00005, 'Number of regular scale size')
flags.DEFINE_bool('is_pretrain', True, 'if True, use pretrain model.')
flags.DEFINE_string('pretrain_model_dir', pretrain_model_dir, 'pretrain model dir.')
flags.DEFINE_string('train_data_dir', train_data_path, 'Directory to put the training data.')
flags.DEFINE_string('test_data_dir', test_data_path, 'Directory to put the training data.')
flags.DEFINE_string('logs_dir', logs_dir, 'direct of summary logs.')

# pretrain model path
model_dir = '/home/alex/Documents/pretraing_model/vgg16'


def makedir(path):
    """
    create dir
    :param path:
    :return:
    """
    a = os.path.exists(path)
    if os.path.exists(path) is False:
        try:
            os.makedirs(path)
            print('{0} has been created'.format(path))
        except Exception as e:
            print(e)


def predict(model_name, image_data, input_op_name, predict_op_name):
    """
    model read and predict
    :param model_name: 
    :param image_data: 
    :param input_op_name: 
    :param predict_op_name: 
    :return: 
    """
    with tf.Graph().as_default():
        with tf.gfile.FastGFile(name=model_name, mode='rb') as model_file:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(model_file.read())
            _ = tf.import_graph_def(graph_def, name='')
        for index, layer in enumerate(graph_def.node):
            print(index, layer.name)

    with tf.Session() as sess:
        init_op = tf.group(
            tf.global_variables_initializer(),
            tf.local_variables_initializer()
        )
        sess.run(init_op)
        image = image_data.eval()
        input = sess.graph.get_tensor_by_name(name=input_op_name)
        output = sess.graph.get_tensor_by_name(name=predict_op_name)

        predict = sess.run(fetches=output, feed_dict={input: image})
        predict_label = np.argmax(predict, axis=1)
        return predict_label


if __name__ == "__main__":

    num_train_samples = get_num_samples(record_dir=FLAGS.train_data_dir)
    num_val_samples = get_num_samples(record_dir=FLAGS.test_data_dir)
    # approximate samples per epoch
    approx_sample = int((num_train_samples // FLAGS.batch_size) * FLAGS.batch_size)
    max_step = int((FLAGS.epoch * approx_sample) // FLAGS.batch_size)
    # max_step = int(FLAGS.epch * num_train_samples / FLAGS.batch_size)

    vgg = VGG16(input_shape=[FLAGS.height, FLAGS.width, FLAGS.depth],
                num_classes=FLAGS.num_classes,
                batch_size=FLAGS.batch_size,
                learning_rate = FLAGS.learning_rate,
                decay_rate=FLAGS.decay_rate,
                num_samples_per_epoch=num_train_samples,
                num_epoch_per_decay=FLAGS.num_epoch_per_decay,
                keep_prob=FLAGS.keep_prop,
                weight_decay=FLAGS.weight_decay,
                is_pretrain=FLAGS.is_pretrain)

    train_images_batch, train_labels_batch, train_filenames = dataset_tfrecord(record_file=FLAGS.train_data_dir,
                                                                  batch_size=FLAGS.batch_size,
                                                                  input_shape=[FLAGS.height, FLAGS.width, FLAGS.depth],
                                                                  class_depth=FLAGS.num_classes,
                                                                  epoch=FLAGS.epoch,
                                                                  shuffle=True,
                                                                  is_training=True)
    val_images_batch, val_labels_batch, val_filenames = dataset_tfrecord(record_file=FLAGS.test_data_dir,
                                                                   batch_size=FLAGS.batch_size,
                                                                   input_shape=[FLAGS.height, FLAGS.width, FLAGS.depth],
                                                                   class_depth=FLAGS.num_classes,
                                                                   epoch=FLAGS.epoch,
                                                                   shuffle=True,
                                                                   is_training=False)

    init_op = tf.group(
        tf.global_variables_initializer(),
        tf.local_variables_initializer()
    )

    # os.environ["CUDA_VISIBLE_DEVICES"] = '0'
    config = tf.ConfigProto()
    # config.gpu_options.per_process_gpu_memory_fraction = 0.5  # maximun alloc gpu50% of MEM
    config.gpu_options.allow_growth = True
    # train and save model
    with tf.Session(config=config) as sess:
        sess.run(init_op)
        # get computer graph
        graph = tf.get_default_graph()

        write = tf.summary.FileWriter(logdir=FLAGS.logs_dir, graph=graph)
        # get model variable of network
        model_variable = tf.model_variables()
        for var in model_variable:
            print(var.name)
        # get and add histogram to summary protocol buffer
        logit_weight = graph.get_tensor_by_name(name='vgg_16/fc8/weights:0')
        tf.summary.histogram(name='logits/weight', values=logit_weight)
        logit_biases = graph.get_tensor_by_name(name='vgg_16/fc8/biases:0')
        tf.summary.histogram(name='logits/biases', values=logit_biases)
        # merges all summaries collected in the default graph
        summary_op = tf.summary.merge_all()
        # load pretrain model
        if FLAGS.is_pretrain:
            # remove variable of fc8 layer from pretrain model
            custom_scope = ['vgg_16/fc8']
            for scope in custom_scope:
                variables = tf.model_variables(scope=scope)
                [model_variable.remove(var) for var in variables]
            saver = tf.train.Saver(var_list=model_variable)
            saver.restore(sess, save_path=FLAGS.pretrain_model_dir)
            print('Successful load pretrain model from {0}'.format(FLAGS.pretrain_model_dir))

        # print(sess.run('vgg_16/conv1/conv1_1/biases:0'))
        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(sess=sess, coord=coord)
        try:
            if not coord.should_stop():

                # ++++++++++++++++++++++++++++++++++start training+++++++++++++++++++++++++++++++++++++++++++++++++
                # used to count the step per epoch
                step_epoch = 0
                print('Epoch: {0}/{1}'.format(step_epoch, FLAGS.epoch))
                for step in range(max_step):
                    train_image, train_label = sess.run([train_images_batch, train_labels_batch])

                    feed_dict = vgg.fill_feed_dict(image_feed=train_image, label_feed=train_label, is_training=True)

                    _, train_loss, train_accuracy, summary = sess.run(fetches=[vgg.train, vgg.loss, vgg.accuracy, summary_op],
                                                             feed_dict=feed_dict)

                    epoch = int(step * FLAGS.batch_size / approx_sample + 1)
                    # print training info
                    print('\tstep {0}:loss value {1}  train accuracy {2}'.format(step_epoch, train_loss, train_accuracy))

                    step_epoch += 1
                    if (step + 1) * FLAGS.batch_size % approx_sample == 0:  # complete training of epoch

                        # ++++++++++++++++++++++++++++++++execute validation++++++++++++++++++++++++++++++++++++++++++++
                        # execute validation when complete every epoch
                        # validation use with all validation dataset
                        val_losses = []
                        val_accuracies = []
                        val_max_steps = int(num_val_samples / FLAGS.batch_size)
                        for _ in range(val_max_steps):
                            val_images, val_labels = sess.run([val_images_batch, val_labels_batch])

                            feed_dict = vgg.fill_feed_dict(image_feed=val_images, label_feed=val_labels, is_training=False)

                            val_loss, val_acc = sess.run([vgg.loss, vgg.accuracy], feed_dict=feed_dict)

                            val_losses.append(val_loss)
                            val_accuracies.append(val_acc)
                        mean_loss = np.array(val_losses, dtype=np.float32).mean()
                        mean_acc = np.array(val_accuracies, dtype=np.float32).mean()

                        print("\t{0}: epoch {1}  val Loss : {2}, val accuracy :  {3}".format(datetime.now(), epoch,
                                                                                           mean_loss, mean_acc))
                        print('Epoch: {0}/{1}'.format(epoch, FLAGS.epoch))
                        step_epoch = 0

                    write.add_summary(summary=summary, global_step=step)
                write.close()

                # save model
                # get op name for save model
                input_op = vgg.raw_input_data.name
                logit_op = vgg.logits.name
                # convert variable to constant
                input_graph_def = tf.get_default_graph().as_graph_def()
                constant_graph = tf.graph_util.convert_variables_to_constants(sess, input_graph_def,
                                                                              [input_op.split(':')[0],
                                                                               logit_op.split(':')[0]])
                # save to serialize file
                makedir(model_dir)
                with tf.gfile.FastGFile(name=os.path.join(model_dir, 'model.pb'), mode='wb') as f:
                    f.write(constant_graph.SerializeToString())

        except Exception as e:
            print(e)
        coord.request_stop()
        coord.join(threads)
    sess.close()
    print('model training has complete')

    # # predict
    # img_path = '/home/alex/Documents/datasets/dogs_and_cat_separate/cat/dog.4.jpg'
    # image = plt.imread(img_path)
    # image = image / 255.
    # image = tf.image.resize(image, FLAGS.depth[:-1])
    # image = tf.expand_dims(image, 0)
    # predict_index = predict(model_name, image, input_op, logit_op)
    # print(predict_index)


    

    



