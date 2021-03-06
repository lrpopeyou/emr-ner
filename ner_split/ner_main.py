#encoding:utf-8
import chardet, os, codecs, argparse, gensim
import numpy as np
from ner_model import BLSTM_CRF
from ner_utils import str2bool, get_logger, get_vocab, get_corpus, get_doc2vec

# hyperparameters
parser = argparse.ArgumentParser(description='CNER')
parser.add_argument('--train_data', type=str, default='train1.txt', help='train data source')
parser.add_argument('--dev_data', type=str, default='dev.txt', help='dev data source')
parser.add_argument('--test_data', type=str, default='testtest.txt', help='test data source')
parser.add_argument('--output_path', type=str, default='/result/', help='output path')
parser.add_argument('--epoch', type=int, default=100, help='#epoch of training')
parser.add_argument('--hidden_dim', type=int, default=300, help='#dim of hidden state')
parser.add_argument('--lr', type=float, default=0.001, help='learning rate')
parser.add_argument('--heads', type=int, default=2, help='multi attention heads')
parser.add_argument('--size_per_head', type=int, default=300, help='multi attention size_per_head')
parser.add_argument('--use_model', type=str, default='self_split', help='self_split, multi_split, self_doc2vec_split or multi_doc2vec_split')
parser.add_argument('--mode', type=str, default='train', help='train or test')
args = parser.parse_args()

#get word embeddings
embedding_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/vectors.npz'
with np.load(embedding_path) as data:
    embeddings = data["embeddings"]
embeddings = np.array(embeddings, dtype='float32')

#get words tags chars vocab
words_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/words.txt'
tags_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/tags.txt'
vocab_words = get_vocab(words_path)
vocab_tags = get_vocab(tags_path)

# paths setting
output_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + args.output_path
if not os.path.exists(output_path): os.makedirs(output_path)
log_path = output_path + 'log.txt'
logger = get_logger(log_path)
logger.info(str(args))

#Model controlled by parameters
use_multi, use_doc2vec = False, False
if args.use_model == 'multi_split':
    use_multi = True
elif args.use_model == 'self_doc2vec_split':
    use_doc2vec = True
elif args.use_model == 'multi_doc2vec_split':
    use_multi, use_doc2vec = True, True
else:
    pass

#training model
if args.mode == 'train':
    train_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/' + args.train_data
    dev_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/' + args.dev_data
    train_data = get_corpus(train_path, vocab_words, vocab_tags)
    dev_data = get_corpus(dev_path, vocab_words, vocab_tags)
    if use_doc2vec == True:
        train_doc2vec_data = get_doc2vec(train_path)
        dev_doc2vec_data = get_doc2vec(dev_path)
        doc2vec_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/doc2vec/split/model'
        doc2vec_model = gensim.models.Doc2Vec.load(doc2vec_path)
        doc2vec_model.delete_temporary_training_data(keep_doctags_vectors=True, keep_inference=True)
        train_doc2vec, dev_doc2vec = [], []
        for j in train_doc2vec_data:
            train_doc2vec_temp = []
            for i in j:
                train_doc2vec_temp.append(doc2vec_model.infer_vector(i, alpha=0.01, steps=1000))
            train_doc2vec.append(train_doc2vec_temp)
        for j in dev_doc2vec_data:
            dev_doc2vec_temp = []
            for i in j:
                dev_doc2vec_temp.append(doc2vec_model.infer_vector(i, alpha=0.01, steps=1000))
            dev_doc2vec.append(dev_doc2vec_temp)
    model = BLSTM_CRF(epoch_num=args.epoch, hidden_dim=args.hidden_dim, embeddings=embeddings, lr=args.lr,
                    vocab_words=vocab_words, vocab_tags=vocab_tags, output_path=output_path, logger=logger,
                    heads=args.heads, size_per_head=args.size_per_head, use_multi=use_multi, use_doc2vec=use_doc2vec)
    model.build_graph()
    if use_doc2vec == True:
        model.train(train_data, dev_data, train_doc2vec, dev_doc2vec)
    else:
        model.train(train_data, dev_data)
elif args.mode == 'test':
    test_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/' + args.test_data
    test_data = get_corpus(test_path, vocab_words, vocab_tags)
    if use_doc2vec == True:
        test_doc2vec_data = get_doc2vec(test_path)
        doc2vec_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/doc2vec/split/model'
        doc2vec_model = gensim.models.Doc2Vec.load(doc2vec_path)
        doc2vec_model.delete_temporary_training_data(keep_doctags_vectors=True, keep_inference=True)
        test_doc2vec = []
        for j in test_doc2vec_data:
            temp_test_doc2vec = []
            for i in j:
                temp_test_doc2vec.append(doc2vec_model.infer_vector(i, alpha=0.01, steps=1000))
            test_doc2vec.append(temp_test_doc2vec)
    model = BLSTM_CRF(epoch_num=args.epoch, hidden_dim=args.hidden_dim, embeddings=embeddings, lr=args.lr,
                    vocab_words=vocab_words, vocab_tags=vocab_tags, output_path=output_path, logger=logger,
                    heads=args.heads, size_per_head=args.size_per_head, use_multi=use_multi, use_doc2vec=use_doc2vec)
    model.build_graph()
    model.restore_session(output_path)
    if use_doc2vec == True:
        model.test(test_data, test_doc2vec)
    else:
        model.test(test_data)
else:
    pass