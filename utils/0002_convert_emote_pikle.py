import pickle
from argparse import ArgumentParser
from pathlib import Path

parser = ArgumentParser()
parser.add_argument('input', help='input pickle file')
args = parser.parse_args()

emote_output_pickle = pickle.load(open(args.input, 'rb'))
blendshape = emote_output_pickle['expression']
