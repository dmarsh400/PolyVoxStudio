import sys
import re
import random
from random import shuffle
from math import sqrt, exp, isnan
from transformers import BertTokenizer, BertModel
import torch.nn as nn
import torch
import numpy as np
import argparse
import json
from app.core.b3 import b3

from collections import Counter

PINK = '\033[95m'
ENDC = '\033[0m'

device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")


class BERTSpeakerID(nn.Module):

    def __init__(self, base_model=None):
        super().__init__()

        modelName=base_model
        modelName=re.sub("^speaker_", "", modelName)
        modelName=re.sub(r"-v\d.*$", "", modelName)
        matcher=re.search(r".*-(\d+)_H-(\d+)_A-.*", modelName)
        bert_dim=0
        modelSize=0
        self.num_layers=0
        if matcher is not None:
            bert_dim=int(matcher.group(2))
            self.num_layers=min(4, int(matcher.group(1)))

            modelSize=self.num_layers*bert_dim

        assert bert_dim != 0

        self.tokenizer = BertTokenizer.from_pretrained(modelName, do_lower_case=False, do_basic_tokenize=False)
        self.tokenizer.add_tokens(["[QUOTE]", "[ALTQUOTE]", "[PAR]", "[CAP]"], special_tokens=True)
        self.bert = BertModel.from_pretrained(modelName)
        self.bert.resize_token_embeddings(len(self.tokenizer))
        self.bert.to(device)
            
        self.tanh = nn.Tanh()
        self.fc = nn.Linear(2*bert_dim, 100)
        self.fc2 = nn.Linear(100, 1)
        
        # Move all components to device
        self.tanh.to(device)
        self.fc.to(device)
        self.fc2.to(device)

    def get_wp_position_for_all_tokens(self, words, doLowerCase=True):

        wps=[]

        # start with 1 for the inital [CLS] token
        cur=1
        for idx, word in enumerate(words):
            if word == "[ALTQUOTE]" or word == "[PAR]" or word == "[QUOTE]":
                word=word

            elif doLowerCase:
                if word[0].lower() != word[0]:
                    word="[CAP] " + word.lower()
                else:
                    word=word.lower()

            target=self.tokenizer.tokenize(word)
            wps.append((cur, cur+len(target)))
            cur+=len(target)
        
        return wps


    def get_batches(self, all_x, all_m, batch_size=32, doLowerCase=True):
                
        batches_o=[]    
        batches_x=[]
        batches_y=[]
        batches_m=[]
            
        for i in range(0, len(all_x), batch_size):
            
            current_batch_input_ids=[]
            current_batch_attention_mask=[]
            current_batch_matrix_cands=[]
            current_batch_matrix_quote=[]
            current_batch_y=[]
            current_batch_eid=[]
            current_quote_eids=[]

            xb=all_x[i:i+batch_size]
            mb=all_m[i:i+batch_size]
            for s, sent in enumerate(xb):

                sent_wp_tokens=[self.tokenizer.convert_tokens_to_ids("[CLS]")]
                attention_mask=[1]

                for word in sent:
                    if word == "[ALTQUOTE]" or word == "[PAR]" or word == "[QUOTE]":
                        word=word

                    elif doLowerCase:
                        if word[0].lower() != word[0]:
                            word="[CAP] " + word.lower()
                        else:
                            word=word.lower()

                    toks = self.tokenizer.tokenize(word)
                    toks = self.tokenizer.convert_tokens_to_ids(toks)
                    sent_wp_tokens.extend(toks)
                    attention_mask.extend([1]*len(toks))
                sent_wp_tokens.append(self.tokenizer.convert_tokens_to_ids("[SEP]"))
                attention_mask.append(1)

                current_batch_input_ids.append(sent_wp_tokens)
                current_batch_attention_mask.append(attention_mask)

            max_len = max([len(s) for s in current_batch_input_ids])

            for j, sent in enumerate(current_batch_input_ids):
                for k in range(len(current_batch_input_ids[j]), max_len):
                    current_batch_input_ids[j].append(0)
                    current_batch_attention_mask[j].append(0)

            for j, (eid, cands, quote) in enumerate(mb):


                wps_all=self.get_wp_position_for_all_tokens(xb[j])

                current_quote_eids.append(eid)

                e1_start_wp, e1_end_wp=wps_all[quote]
                matrix_cands=np.zeros((10,max_len))
                matrix_quote=np.zeros((10,max_len))

                # CAND_FILTER_PATCH: prune & rank candidates near the quote, prefer proper names, demote generics
                def _looks_proper(span):
                    # crude: first token Titlecase (not [CAP] tokenized form here)
                    try:
                        w = xb[j][span[0]]
                        return bool(re.match(r'^[A-Z][\w\-]*$', w))
                    except Exception:
                        return False

                def _near_verb(span):
                    verbs = {'said','asked','replied','whispered','shouted','told','called','answered','muttered','cried','yelled','snapped','remarked','observed','insisted','pleaded'}
                    s, e = span[0], span[1]
                    L = max(0, s-4)
                    R = min(len(xb[j]), e+4)
                    window = [w.lower() for w in xb[j][L:R]]
                    return any(w in verbs for w in window)

                def _is_generic(span):
                    s, e = span[0], span[1]
                    name_text = ' '.join(xb[j][s:e]).lower()
                    if re.match(r'^(the\s+)?(king|queen|prince|princess|duke|duchess)$', name_text):
                        return True
                    return re.match(r'^(the\s+)?(old|older|young|tall|short)\s+(man|woman|men|women)$', name_text) is not None
                def _is_deity(span):
                    s, e = span
                    name = ' '.join(xb[j][s:e]).lower()
                    return name in {'god','lord','jesus','christ'}

                def _surname_alone_penalty(span, all_cands):
                    """If this candidate is a single token and any other candidate is a
                    multi-token whose LAST token is the same (e.g., 'King' vs 'Steve King'),
                    penalize the single-token so the full name wins."""
                    s, e = span
                    tokens = xb[j][s:e]
                    if len(tokens) != 1:
                        return 0.0
                    last = tokens[0].lower()
                    for (s2, e2, _, _) in all_cands:
                        if (e2 - s2) >= 2:
                            last2 = xb[j][e2-1].lower()
                            if last == last2:
                                return 2.5
                    return 0.0


                quote_idx = quote  # token index of the quote span start in this representation
                scored = []
                for (start, end, truth, cand_eid) in cands:
                    # distance to quote (closer is better)
                    dist = min(abs(start - quote_idx), abs((end-1) - quote_idx))
                    score = -float(dist)
                    if _looks_proper((start,end)):
                        score += 2.0
                    if _near_verb((start,end)):
                        score += 1.0
                    if _is_generic((start,end)):
                        score -= 5.0
                    # light penalty if far (>60 tokens) from quote
                    if dist > 60:
                        score -= 10.0
                    if _is_deity((start,end)):
                        score -= 6.0
                    scored.append((score, start, end, truth, cand_eid))

                scored.sort(key=lambda x: x[0], reverse=True)
                cands_use = [(s,e,t,i) for (_, s,e,t,i) in scored[:10]]
                for l in range(10):
                    for k in range(e1_start_wp, e1_end_wp):
                        matrix_quote[l][k]=1./(e1_end_wp-e1_start_wp)

                y=[]
                eids=[]
                for c_idx, (start, end, truth, cand_eid) in enumerate(cands_use):

                    e2_start_wp, _=wps_all[start]
                    _, e2_end_wp=wps_all[end-1]

                    for k in range(e2_start_wp, e2_end_wp):
                        matrix_cands[c_idx][k]=1./(e2_end_wp-e2_start_wp)

                    y.append(truth)
                    eids.append(cand_eid)

                for l in range(len(y), 10):
                    y.append(0)
                    eids.append(None)

                current_batch_matrix_cands.append(matrix_cands)
                current_batch_matrix_quote.append(matrix_quote)
                current_batch_y.append(y)
                current_batch_eid.append(eids)


            batches_o.append((xb, mb))
            batches_x.append({"toks": torch.LongTensor(current_batch_input_ids).to(device), "mask":torch.LongTensor(current_batch_attention_mask).to(device)})
            batches_m.append({"cands":torch.FloatTensor(np.array(current_batch_matrix_cands)).to(device), "quote":torch.FloatTensor(np.array(current_batch_matrix_quote)).to(device)})
            batches_y.append({"y":torch.LongTensor(current_batch_y).to(device), "eid":current_batch_eid, "quote_eids":current_quote_eids})

        return batches_x, batches_m, batches_y, batches_o
    

    def forward(self, batch_x, batch_m): 
        
        _, pooled_outputs, sequence_outputs = self.bert(batch_x["toks"], token_type_ids=None, attention_mask=batch_x["mask"], output_hidden_states=True, return_dict=False)

        out=sequence_outputs[-1]
        batch_size, _, bert_size=out.shape

        combined_cands=torch.matmul(batch_m["cands"],out)
        combined_quote=torch.matmul(batch_m["quote"],out)
        
        combined=torch.cat((combined_cands, combined_quote), axis=2)

        preds = self.fc(combined)
        preds=self.tanh(preds)
        preds = self.fc2(preds)

        return preds


    def evaluate(self, dev_x_batches, dev_m_batches, dev_y_batches, dev_o_batches, epoch):

        self.eval()

        cor=0.
        tot=0.
        nones=0

        gold_eids={}
        pred_eids={}

        with torch.no_grad():

            idd=0
            for x1, m1, y1, o1 in zip(dev_x_batches, dev_m_batches, dev_y_batches, dev_o_batches):
                y_pred = self.forward(x1, m1)

                orig, meta=o1
                predictions=torch.argmax(y_pred, axis=1).detach().cpu().numpy()
                for idx, pred in enumerate(predictions):

                    sent=orig[idx]

                    gold_eids[idd]=y1["quote_eids"][idx]

                    predval=y1["eid"][idx][pred[0]]
                    if predval is None:
                        predval="none-%s" % (idd)

                    pred_eids[idd]=predval
                    val=y1["y"][idx][pred[0]]

                    if pred[0] < len(meta[idx][1]):
                        ent_start, ent_end, lab, ent_eid=meta[idx][1][pred[0]]

                        if epoch == "test":
                            print("epoch %s" % epoch, ' '.join(sent[:ent_start]), PINK, ' '.join(sent[ent_start:ent_end]), "(%s)" % int(val.detach().cpu().numpy()), ENDC, ' '.join(sent[ent_end:]))

                    if val == 1:
                        cor+=1
                    tot+=1

                    idd+=1

        precision, recall, F=b3(gold_eids, pred_eids)
        print("Nones: %s" % nones)
        print("Epoch %s, Quote F1: %.3f\tP: %.3f, R: %.3f" % (epoch, F, precision, recall))
        print("Epoch %s, accuracy: %.3f" % (epoch, cor/tot))

        return F, cor/tot