# -*- coding: utf-8 -*-

import os
import shutil

from CartPole.DDPG.agent import Agent

import tensorflow as tf


class Critic(Agent):
    def __init__(self, sess, env, learning_rate=0.001):
        super(Critic, self).__init__(env)

        self.sess = sess
        self.log_dir = 'log/critic'

        # Estimate Critic Network
        with tf.variable_scope("Critic"):
            self.q_value = self.critic_network()
            self.critic_para = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES,
                                                 scope="Critic/Network")

        # Target Critic Network
        with tf.variable_scope("Target_Critic"):
            self.target_q_value = self.critic_network()
            self.target_critic_para = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES,
                                                        scope="Critic/Network")

        # Update Estimate Network
        with tf.variable_scope("Critic/Update"):
            # todo Maybe Something is Wrong
            # Get Target_Q_Value from outside
            self.loss = tf.reduce_mean(tf.squared_difference(self.q_value, self.target_q_value),
                                       name='TD-Loss')
            self.optimizer = tf.train.RMSPropOptimizer(learning_rate, name='Optimizer')
            self.estimate_update = self.optimizer.minimize(self.loss)
            tf.summary.scalar(name='TD-Loss', tensor=self.loss)

        # Update Target Network
        with tf.variable_scope("Target_Critic/Update"):
            self.target_update = [tf.assign(t, self.tau * t + (1-self.tau) * e)
                                  for t, e in zip(self.target_critic_para, self.critic_para)]

        # TensorBoard Data Flow
        with tf.variable_scope('C_Summary'):
            self.merge = tf.summary.merge_all()
            if os.path.exists(self.log_dir):
                shutil.rmtree(self.log_dir)
            self.writer = tf.summary.FileWriter(logdir=self.log_dir + '/train')

        # Initialize TensorFlow Session
        self.sess.run(tf.global_variables_initializer())

    def critic_network(self):
        with tf.variable_scope('Network', reuse=tf.AUTO_REUSE):
            init_w = tf.random_normal_initializer(0., 0.1)
            init_b = tf.constant_initializer(0.1)

            with tf.variable_scope('layer'):
                n = 8
                weight_state = tf.get_variable('weight_state',
                                               [self.state_dim, n],
                                               initializer=init_w)
                weight_action = tf.get_variable('weight_action',
                                                [self.action_dim, n],
                                                initializer=init_w)

                bias = tf.get_variable('Bias', n, initializer=init_b)

                tf.summary.histogram("State_Weight", weight_state)
                tf.summary.histogram("Action_Weight", weight_action)
                tf.summary.histogram("Bias", bias)

                network = tf.nn.relu(tf.matmul(self.state, weight_state) +
                                     tf.matmul(self.action, weight_action) +
                                     bias)

            with tf.variable_scope('Q_Value'):
                q_value = tf.layers.dense(inputs=network,
                                          units=1,
                                          kernel_initializer=init_w,
                                          bias_initializer=init_b)
        return q_value

    # Get Q-Value from Estimate Network or Target Network
    def get_q_value(self, network_type, state, action):
        action = [Agent.num_2_one_hot(a_item, self.action_dim) for a_item in action]
        if network_type == 'Estimate':
            return self.sess.run(self.q_value, feed_dict={self.state: state, self.action: action})
        else:
            return self.sess.run(self.target_q_value, feed_dict={self.state: state, self.action: action})

    # Update Estimate Network or Target Network
    def update(self, *, update_type, target_q_value=None, state=None, action=None, iter_num=None):
        # Update Estimate Critic Network by minimize Loss Function
        if update_type == 'Estimate':
            action = [Agent.num_2_one_hot(a_item, self.action_dim) for a_item in action]
            summary, _ = self.sess.run([self.merge, self.estimate_update], feed_dict={
                # State + Action == Estimate Q-Value
                self.state: state,
                self.action: action,
                # Target Q-Value from outside
                self.target_q_value: target_q_value
            })
            self.writer.add_summary(summary, iter_num)
        else:
            self.sess.run(self.target_update)
