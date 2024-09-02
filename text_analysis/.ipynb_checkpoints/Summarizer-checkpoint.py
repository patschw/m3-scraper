# -*- coding: utf-8 -*-
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import transformers
import torch
from nltk import ngrams

# TheBloke/em_german_mistral_v01-GPTQ --> for GPU inference
# TheBloke/em_german_mistral_v01-GGUF --> for CPU inference
# VAGOsolutions/Llama-3-SauerkrautLM-8b-Instruct --> German Llama
# Aleph-Alpha/Pharia-1-LLM-7B-control


class Summarizer:
    """A summarizer that uses a llama model to generate summaries."""
    def __init__(self, model_name_or_path = "TheBloke/em_german_leo_mistral-GPTQ"):

        # To use a different branch, change revision
        # For example: revision="gptq-4bit-32g-actorder_True"
        self.model = AutoModelForCausalLM.from_pretrained(model_name_or_path,
                                                     device_map="auto",
                                                     trust_remote_code=False,
                                                     revision="main")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)
        

    def summarize(self, articles_list):
        output_list = articles_list
        for single_article_dict in output_list:
            original_text = single_article_dict.get("main_text", "")

            summary = self._generate_summary(original_text)

            # Ensure no 6 consecutive words from the original text appear in the summary
            while self._has_six_consecutive_words(original_text, summary):
                summary = self._generate_summary(original_text)

            single_article_dict["summary"] = summary
            # single_article_dict["summary"] = "palceholder for summary"

        return output_list

    def _generate_summary(self, original_text):
        prompt_template=f'''"Du bist ein sehr genauer und hilfreicher deutscher KI-Text-Zusammenfasser. 
                    Die Texte von Nachrichten-Websiten, die ich dir gebe, fasst du zusammen. Dabei verwendest du nie mehr als 6 Wörter des Originaltextes hintereinander. 
                    Es ist sehr wichtig, dass du dich an diese Vorgabe hältst. Also beachte: Du produzierst Zusammenfassungen der Texte, die ich dir gebe. 
                    Diese Zusammenfassungen dürfen niemals mehr als 6 aufeinanderfolgende Wörter des Originaltextes enthalten. 
                    Nutze Paraphrasierung, Synonyme und andere Techniken, um sicherzugehen, dass niemals mehr als 6 aufeinanderfolgende Wörter des Originaltextes in der Zusammenfassunge enthalten sind.
                    Stelle dabei aber sicher, dass Sinn und Inhalt des Originaltextes möglichst erhalten bleiben. HIER  DER TEXT DEN DU ZUSAMMEFASSEN SOLLST: {original_text} HIER DEINE ZUSAMMENFASSUNG:
        '''

        # FRAGE MARIO: WOLLEN WIR VERSCHIEDENE LAENGEN FUER DIE SUMMARIES?
        #max_output_tokens = int(len(original_text)/4)
        
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=1024,
            #max_length=4096,
            do_sample=True,
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            repetition_penalty=1.1
        )

        summary = pipe(prompt_template)[0]['generated_text']
        return summary

    def _has_six_consecutive_words(self, original_text, summary):
        original_text_ngrams = set(ngrams(original_text.split(), 6))
        summary_ngrams = set(ngrams(summary.split(), 6))
        return bool(original_text_ngrams & summary_ngrams)
