import argparse
import cPickle
from rltools.utils.dataloader import DataLoader
import h5py
import matplotlib.pyplot as plt
import numpy as np
import random
import tensorflow as tf
import time
import vae

def safezip(*ls):
    assert all(len(l) == len(ls[0]) for l in ls)
    return zip(*ls)

# Export model parameters to h5 file
def save_h5(args, net):
    # Begin tf session
    with tf.Session() as sess:
        tf.initialize_all_variables().run()
        saver = tf.train.Saver(tf.all_variables())

        # load from previous save
        if len(args.ckpt_name) > 0:
            saver.restore(sess, os.path.join(args.save_dir, args.ckpt_name))
        else:
            print 'checkpoint name not specified... exiting.'
            return

        vs = tf.get_collection(tf.GraphKeys.VARIABLES)
        vals = sess.run(vs)
        exclude1 = ["Adam", "beta", "learning_rate", "kl_weight"]
        exclude2 = ["learning_rate", "kl_weight"]
        encoder = ["rnn_decoder", "latent"]

        with h5py.File('encoder.h5', 'a') as f:
            dset = f.create_group('snapshots/encoder')
            for v, val in safezip(vs, vals):
                if all([e not in v.name for e in exclude1]):
                    if any([e in v.name for e in encoder]):
                        dset[v.name] = val

        with h5py.File('policy.h5', 'a') as f:
            dset = f.create_group('snapshots/policy')
            for v, val in safezip(vs, vals):
                if all([e not in v.name for e in exclude2]):
                    if all([e not in v.name for e in encoder]):
                        if val.ndim == 1:
                            val = np.expand_dims(val, axis=0)
                        if 'beta' in v.name or 'Adam' in v.name:
                            dset['policy/optimizer/' + v.name] = val
                        else:
                            dset[v.name] = val

# Visualize samples from latent space
def latent_viz(args, net, e, sess, data_loader):
    # Generate passive samples
    data_loader.batchptr_pass = 0
    full_sample_pass = 0.0
    print 'generating z samples passive...'
    for b in xrange(data_loader.n_batches_pass):
        batch_dict = data_loader.next_batch_pass()
        s = batch_dict["states"]
        a = batch_dict["actions"]
        z_mean, z_logstd, state = net.encode(sess, s, a, args)

        samples = np.random.normal(size=(args.sample_size, args.batch_size, args.z_dim))
        z_samples = samples * np.exp(z_logstd) + z_mean
        z_samples = np.reshape(z_samples, (args.sample_size*args.batch_size, args.z_dim))
        if type(full_sample_pass) is float:
            full_sample_pass = z_samples
        else:
            full_sample_pass = np.concatenate((full_sample_pass, z_samples), axis=0)

    # Generate aggressive samples
    data_loader.batchptr_agg = 0
    full_sample_agg = 0.0
    print 'generating z samples aggressive...'
    for b in xrange(data_loader.n_batches_agg):
        batch_dict = data_loader.next_batch_agg()
        s = batch_dict["states"]
        a = batch_dict["actions"]
        z_mean, z_logstd, state = net.encode(sess, s, a, args)

        samples = np.random.normal(size=(args.sample_size, args.batch_size, args.z_dim))
        z_samples = samples * np.exp(z_logstd) + z_mean
        z_samples = np.reshape(z_samples, (args.sample_size*args.batch_size, args.z_dim))
        if type(full_sample_agg) is float:
            full_sample_agg = z_samples
        else:
            full_sample_agg = np.concatenate((full_sample_agg, z_samples), axis=0)

    # Select random subset of values in full set of samples
    ind_pass = random.sample(xrange(0, len(full_sample_pass)), 2000)
    ind_agg = random.sample(xrange(0, len(full_sample_agg)), 2000)

    # Plot and save results
    print 'saving and exiting.'
    plt.cla()
    plt.rc('text', usetex=True)
    plt.rc('font', family='serif')
    plt.plot(full_sample_pass[ind_pass, 0], full_sample_pass[ind_pass, 1], 'ro', label='Passive')
    plt.plot(full_sample_agg[ind_agg, 0], full_sample_agg[ind_agg, 1], 'bx', label='Aggressive')
    plt.ylim(-8, 8)
    plt.xlim(-8, 8)
    plt.xlabel(r'$z_1$', fontsize=16)
    plt.ylabel(r'$z_2$', fontsize=16)
    plt.title('Epoch ' + str(e))
    plt.legend(loc='upper right')
    plt.grid()
    plt.savefig('./images/latent_viz_'+str(e)+'.pdf')
