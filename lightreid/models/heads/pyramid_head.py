"""
@author:    Guan'an Wang
@contact:   guan.wang0706@gmail.com
"""

import torch
import torch.nn as nn
from .bn_head import BNHead


class PyramidHead(nn.Module):
    """Pyramid Head.
    Learn multiple codes of different lengths.

    Reference:
    Paper: Wang et al. Faster Person Re-identification. ECCV 2020.

    Args:
        in_dim (int): input feature dimension
        out_dims (list): out feature dimensions, e.g. out_dims=[2048, 512, 128, 32]
    """

    def __init__(self, in_dim, out_dims, class_num):
        super(PyramidHead, self).__init__()
        self.in_dim = in_dim
        self.eval_dims = out_dims
        self.class_num = class_num
        self.train_dims = [2048, 1024, 512, 256, 128, 64, 32]

        setattr(self, 'neck{}'.format(int(in_dim)), BNHead(int(in_dim), self.class_num))
        for idx, dim in enumerate(self.train_dims):
            if idx == 0:
                setattr(self, 'fc{}'.format(int(dim)), nn.Linear(in_dim, int(dim)))
                setattr(self, 'neck{}'.format(int(dim)), BNHead(int(dim), self.class_num))
            else:
                setattr(self, 'fc{}'.format(int(dim)), nn.Linear(int(self.train_dims[idx - 1]), int(dim)))
                setattr(self, 'neck{}'.format(int(dim)), BNHead(int(dim), self.class_num))

    def forward(self, feats, y=None, use_tanh=False):

        neck = getattr(self, 'neck{}'.format(int(self.in_dim)))

        if self.training:
            bn_feats, logits = neck(feats, use_tanh=use_tanh)
            feats_list = [feats]
            bnfeats_list = [bn_feats]
            logits_list = [logits]
        else:
            binary_codes = neck(feats, use_tanh=use_tanh)
            binary_codes_list = [binary_codes]

        for idx, dim in enumerate(self.train_dims):
            fc = getattr(self, 'fc{}'.format(int(dim)))
            neck = getattr(self, 'neck{}'.format(int(dim)))
            feats = fc(feats.detach())

            if self.training:
                bn_feats, logits = neck(feats, use_tanh=use_tanh)
                feats_list.append(feats)
                bnfeats_list.append(bn_feats)
                logits_list.append(logits)
            else:
                binary_codes = neck(feats, use_tanh=use_tanh)
                binary_codes_list.append(binary_codes)

        if self.training:
            return feats_list, bnfeats_list, logits_list
        else:
            binary_codes_list = binary_codes_list[1:]
            return [val for val in binary_codes_list if val.shape[1] in self.eval_dims]
