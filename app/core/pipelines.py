import re
from spacy.tokens import Doc

class Entity:
    def __init__(self, start, end, entity_id=None, quote_id=None, quote_eid=None, proper=None, ner_cat=None, in_quote=None, text=None):
        # print("creating")
        self.start=start
        self.end=end
        self.entity_id=entity_id
        self.quote_id=quote_id
        self.proper=proper
        self.ner_cat=ner_cat
        self.in_quote=in_quote
        self.quote_eid=quote_eid
        self.text=text
        self.quote_mention=None
        self.global_start=None
        self.global_end=None

    def __str__(self):
        return ("%s %s %s %s %s %s %s %s" % (self.global_start, self.global_end, self.entity_id, self.proper, self.ner_cat, self.in_quote, self.quote_eid, self.text))


class Token:
    def __init__(self, paragraph_id, sentence_id, index_within_sentence_idx, token_id, text, pos, fine_pos, lemma, deprel, dephead, ner, startByte):
        self.text=text
        self.paragraph_id=paragraph_id
        self.sentence_id=sentence_id
        self.index_within_sentence_idx=index_within_sentence_idx
        self.token_id=token_id
        self.lemma=lemma
        self.pos=pos
        self.fine_pos=fine_pos
        self.deprel=deprel
        self.dephead=dephead
        self.ner=ner
        self.startByte=startByte
        self.endByte=startByte+len(text)
        self.inQuote=False
        self.event="O"

    def __str__(self):
        return '\t'.join([str(x) for x in [self.paragraph_id, self.sentence_id, self.index_within_sentence_idx, self.token_id, self.text, self.lemma, self.startByte, self.endByte, self.pos, self.fine_pos, self.deprel, self.dephead, self.event]])

    @classmethod 
    def convert(self, sents):
        toks=[]
        i=0
        cur=0
        for sidx, sent in enumerate(sents):
            for widx, word in enumerate(sent):
                token=Token(0, sidx, widx, i, word, None, None, None, None, None, None, cur)
                toks.append(token)
                i+=1
                cur+=len(word) + 1
        return toks

    @classmethod 
    def deconvert(self, toks):
        sents=[]
        sent=[]
        lastSid=None
        for tok in toks:
            if lastSid is not None and tok.sentence_id != lastSid:
                sents.append(sent)
                sent=[]
            sent.append(tok)
            lastSid=tok.sentence_id

        if len(sent) > 0:
            sents.append(sent)

        # print(sents)
        return sents


class SpacyPipeline:
    def __init__(self, spacy_nlp):
        self.spacy_nlp=spacy_nlp
        self.spacy_nlp.max_length = 10000000

    # IMPORTANT: preserve original text (no S/N/T substitutions)
    def filter_ws(self, text):
        return text

    def tag_pretokenized(self, toks, sents, spaces):
        doc = Doc(self.spacy_nlp.vocab, words=toks, spaces=spaces)
        for idx, token in enumerate(doc):
            token.sent_start=sents[idx]
        for name, proc in self.spacy_nlp.pipeline:
            doc = proc(doc)
        return self.process_doc(doc)

    def tag(self, text):
        doc = self.spacy_nlp(text)
        return self.process_doc(doc)

    def process_doc(self, doc):
        tokens=[]
        skipped_global=0
        paragraph_id=0
        current_whitespace=""
        sentence_id=0

        for sid, sent in enumerate(doc.sents):
            skipped_in_sentence=0
            skips_in_sentence=[]
            curSkips=0
            for w_idx, tok in enumerate(sent):
                if tok.is_space:
                    curSkips+=1
                skips_in_sentence.append(curSkips)

            hasWord=False

            for w_idx, tok in enumerate(sent):
                if tok.is_space:
                    skipped_global+=1
                    skipped_in_sentence+=1
                    current_whitespace+=tok.text
                else:
                    # paragraph boundary if we saw a blank line in whitespace buffer
                    if re.search(r"\n\s*\n", current_whitespace) is not None:
                        paragraph_id+=1
                    hasWord=True

                    head_in_sentence=tok.head.i-sent.start
                    skips_between_token_and_head=skips_in_sentence[head_in_sentence]-skips_in_sentence[w_idx]

                    # use ORIGINAL token text (no substitutions)
                    token=Token(
                        paragraph_id,
                        sentence_id,
                        w_idx-skipped_in_sentence,
                        tok.i-skipped_global,
                        tok.text,
                        tok.pos_,
                        tok.tag_,
                        tok.lemma_,
                        tok.dep_,
                        tok.head.i-skipped_global-skips_between_token_and_head,
                        None,
                        tok.idx
                    )
                    tokens.append(token)
                    current_whitespace=""

            if hasWord:
                sentence_id+=1

        return tokens


class StanzaPipeline:
    def __init__(self, nlp):
        self.nlp=nlp

    # Keep original text intact here too
    def filter_ws(self, text):
        return text

    def tag(self, text):
        text=re.sub(r"\s+", " ", text)
        doc = self.nlp(text)
        tokens=[]
        tid=0
        cur=0
        for sid, sent in enumerate(doc.sentences):
            for w_idx, tok in enumerate(sent.words):
                feats=tok.misc.split("|") if tok.misc else []
                start_char=-1
                for f in feats:
                    parts=f.split("=")
                    if parts[0] == "start_char" and len(parts) > 1:
                        start_char=int(parts[1])

                paragraph_id=-1
                token=Token(
                    paragraph_id, sid, w_idx, tid,
                    tok.text, tok.upos, tok.pos, tok.lemma, tok.deprel,
                    cur+tok.head-1, None, start_char
                )
                tokens.append(token)
                tid+=1
            cur+=len(sent.words)

        return tokens
