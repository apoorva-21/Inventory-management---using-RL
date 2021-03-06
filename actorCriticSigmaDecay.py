"""
Actor-Critic with continuous action using TD-error as the Advantage, Reinforcement Learning.

The Pendulum example (based on https://github.com/dennybritz/reinforcement-learning/blob/master/PolicyGradient/Continuous%20MountainCar%20Actor%20Critic%20Solution.ipynb)

Cannot converge!!! oscillate!!!

View more on my tutorial page: https://morvanzhou.github.io/tutorials/

Using:
tensorflow r1.3
gym 0.8.0
"""
#TODO
# ADD WEIGHT SAVE FUNCTION

# TRY PPO and DDPG too

'''CHANGES MADE : 
    
    ACTIVATIONS OF THE MU & SIGMA NETWORK:SIGMOID->LEAKY ReLU

    LEARNING RATE SET TO 0.001

   Done SCALING OF THE REWARDS TO PREVENT BLOWUP

MENTION IN PAPER:
    -EMPIRICALLY DETERMINED LEARNING RATES FOR BOTH A AND C
'''
#RUNS SUCCESSFULLY ON : environment_single_sku.py
import tensorflow as tf
import numpy as np
from environment2sku import InventoryEnv
import time
np.random.seed(2)
tf.set_random_seed(2)  # reproducible

INITIAL_SD = 100
FINAL_SD = 1

class Actor(object):
    def __init__(self, sess, n_features,n_outputs, action_bound, lr=0.0001):
        self.sess = sess

        self.s = tf.placeholder(tf.float32, [1, n_features], "state")
        self.a = tf.placeholder(tf.float32, None, name="act")

        self.initial_sd = tf.Variable(INITIAL_SD, dtype = tf.float32)
        
        self.td_error = tf.placeholder(tf.float32, None, name="td_error")  # TD_error

        l1 = tf.layers.dense(
            inputs=self.s,
            units=30,  # number of hidden units
            activation=tf.nn.sigmoid,
            kernel_initializer=tf.random_normal_initializer(0., .1),  # weights
            bias_initializer=tf.constant_initializer(0.1),  # biases
            name='l1'
        )

        mu = tf.layers.dense(
            inputs=l1,
            units=n_outputs,  # number of hidden units
            activation=tf.nn.leaky_relu,
            kernel_initializer=tf.random_normal_initializer(0., .1),  # weights
            bias_initializer=tf.constant_initializer(0.1),  # biases
            name='mu'
        )

        '''sigma = tf.layers.dense(
            inputs=l1,
            units=n_outputs,  # output units
            activation=tf.nn.leaky_relu,  # get action probabilities
            kernel_initializer=tf.random_normal_initializer(0., .1),  # weights
            bias_initializer=tf.constant_initializer(1.),  # biases
            name='sigma'
        )'''

        global_step = tf.Variable(0, trainable=False)
        
        self.sd = tf.clip_by_value(tf.train.exponential_decay(self.initial_sd, global_step, 10, 0.99634), FINAL_SD, INITIAL_SD)


        # self.e = epsilon = tf.train.exponential_decay(2., global_step, 1000, 0.9)
        self.mu = mu
        self.normal_dist = tf.distributions.Normal(self.mu, self.sd)
        self.action = tf.clip_by_value(self.normal_dist.sample(1), action_bound[0], action_bound[1])

        with tf.name_scope('exp_v'):
            log_prob = self.normal_dist.log_prob(self.a)  # loss without advantage
            self.exp_v = log_prob * self.td_error  # advantage (TD_error) guided loss
            # Add cross entropy cost to encourage exploration
            self.exp_v += 0.01*self.normal_dist.entropy()

        with tf.name_scope('train'):
            self.train_op = tf.train.AdamOptimizer(lr).minimize(-self.exp_v, global_step)    # min(v) = max(-v)

    def learn(self, s, a, td):
        s = s[np.newaxis, :]
        feed_dict = {self.s: np.squeeze(s, 2), self.a: a, self.td_error: td}
        _, exp_v = self.sess.run([self.train_op, self.exp_v], feed_dict)
        return exp_v

    def choose_action(self, s, i_episode):
        s = s[np.newaxis, :]
        a, myMu, mySD = self.sess.run([self.action, self.mu, self.sd], {self.s: np.squeeze(s,2)})  # get probabilities for all actions
        # a, m1, s1 = self.sess.run([self.action, self.mu, self.sigma] , {self.s: np.squeeze(s,2)})  # get probabilities for all actions
        # print 'Mean : {}\t Std Dev : {}'.format(m1,s1)
        # time.sleep(0.5)
        # if i_episode > 60:
        # print 'Mean: {}\tStd. Dev: {}\tAction: {}'.format(np.squeeze(myMu), mySD, np.squeeze(a))
        a = np.squeeze(a,1)
        # a = a.T **WRONGGGGGG
        return a.astype(np.int)

class Critic(object):
    def __init__(self, sess, n_features, lr=0.01):
        self.sess = sess
        with tf.name_scope('inputs'):
            self.s = tf.placeholder(tf.float32, [1, n_features], "state")
            self.v_ = tf.placeholder(tf.float32, [1, 1], name="v_next")
            self.r = tf.placeholder(tf.float32, name='r')

        with tf.variable_scope('Critic'):
            l1 = tf.layers.dense(
                inputs=self.s,
                units=30,  # number of hidden units
                activation=tf.nn.relu,
                kernel_initializer=tf.random_normal_initializer(0., .1),  # weights
                bias_initializer=tf.constant_initializer(0.1),  # biases
                name='l1'
            )

            self.v = tf.layers.dense(
                inputs=l1,
                units=1,  # output units
                activation=None,
                kernel_initializer=tf.random_normal_initializer(0., .1),  # weights
                bias_initializer=tf.constant_initializer(0.1),  # biases
                name='V'
            )

        with tf.variable_scope('squared_TD_error'):
            self.td_error = tf.reduce_mean(self.r + GAMMA * self.v_ - self.v)
            self.loss = tf.square(self.td_error)    # TD_error = (r+gamma*V_next) - V_eval
        with tf.variable_scope('train'):
            self.train_op = tf.train.AdamOptimizer(lr).minimize(self.loss)

    def learn(self, s, r, s_):
        s, s_ = s[np.newaxis, :], s_[np.newaxis, :]

        v_ = self.sess.run(self.v, {self.s: np.squeeze(s_, 2)})
        td_error, _ = self.sess.run([self.td_error, self.train_op],
                                          {self.s: np.squeeze(s, 2), self.v_: v_, self.r: r})
        return td_error


OUTPUT_GRAPH = False
MAX_EPISODE = 2000
MAX_EP_STEPS = 200
DISPLAY_REWARD_THRESHOLD = -100  # renders environment if total episode reward is greater then this threshold
RENDER = False  # rendering wastes time
GAMMA = 0.9
LR_A = 0.01    # learning rate for actor
LR_C = 0.001     # learning rate for critic

env = InventoryEnv()
# env.seed(1)  # reproducible
# env = env.unwrapped

N_S = env.observation_space.shape[0]
N_O = env.action_space.shape[0] * env.action_space.shape[1]
A_BOUND_L = env.action_space.low
A_BOUND_H = env.action_space.high
sess = tf.Session()

actor = Actor(sess, n_features=N_S, n_outputs = N_O,lr=LR_A, action_bound=[A_BOUND_L, A_BOUND_H])
critic = Critic(sess, n_features=N_S, lr=LR_C)

sess.run(tf.global_variables_initializer())

if OUTPUT_GRAPH:
    tf.summary.FileWriter("logs/", sess.graph)

for i_episode in range(MAX_EPISODE):
    s = env.reset()
    t = 0
    ep_rs = []
    tot_reward = 0
    # ep_time = 0
    while True:
        # if i_episode > MAX_EPISODE - 10 or i_episode % 10 == 0:
        # env.render()
        a = actor.choose_action(s, i_episode)
        # print a
        #RESHAPE THE ACTION ACC TO THE N_WHOUSES AND N_PRODUCTS
        s_, r = env.step(np.reshape(a, (env.action_space.shape[0], env.action_space.shape[1])))

        # ep_time += 1
        #r /= 10

        td_error = critic.learn(s, r, s_)  # gradient = grad[r + gamma * V(s_) - V(s)]
        actor.learn(s, a, td_error)  # true_gradient = grad[logPi(s,a) * td_error]

        # if i_episode > 40:
        #     print 
        s = s_
        t += 1
        tot_reward += r
        ep_rs.append(r)
        if t > MAX_EP_STEPS:
        	# time.sleep(2)
        	print 'EPISODE NUMBER : {}\tTOTAL REWARD : {}'.format(i_episode,tot_reward)
        	ep_rs_sum = sum(ep_rs)
        	if 'running_reward' not in globals():
        		running_reward = ep_rs_sum
        	else:
        		running_reward = running_reward * 0.9 + ep_rs_sum * 0.1
        	if running_reward > DISPLAY_REWARD_THRESHOLD: RENDER = True  # rendering
        	# print("episode:", i_episode, "  reward:", tot_reward)#int(running_reward))
        	break

