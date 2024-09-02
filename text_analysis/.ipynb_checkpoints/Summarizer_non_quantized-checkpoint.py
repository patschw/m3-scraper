# -*- coding: utf-8 -*-
import transformers
import torch
from nltk import ngrams

# TheBloke/em_german_mistral_v01-GPTQ --> for GPU inference
# TheBloke/em_german_mistral_v01-GGUF --> for CPU inference
# VAGOsolutions/Llama-3-SauerkrautLM-8b-Instruct --> German Llama




class Summarizer:
    """A summarizer that uses a llama model to generate summaries."""
    def __init__(self, model_id="VAGOsolutions/Llama-3.1-SauerkrautLM-8b-Instruct"):
        self.pipeline = transformers.pipeline(
            "text-generation",
            model=model_id,
            model_kwargs={"torch_dtype": torch.bfloat16},
            device_map="auto",
        )
        

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
        messages = [
        {"role": "system", "content": """Du bist ein sehr genauer und hilfreicher deutscher KI-Text-Zusammenfasser. 
            Die Texte von Nachrichten-Websiten, die ich dir gebe, fasst du zusammen. Dabei verwendest du nie mehr als 6 Wörter des Originaltextes hintereinander. 
            Es ist sehr wichtig, dass du dich an diese Vorgabe hältst. Also beachte: Du produzierst Zusammenfassungen der Texte, die ich dir gebe. 
            Diese Zusammenfassungen dürfen niemals mehr als 6 aufeinanderfolgende Wörter des Originaltextes enthalten. 
            Nutze Paraphrasierung, Synonyme und andere Techniken, um sicherzugehen, dass niemals mehr als 6 aufeinanderfolgende Wörter des Originaltextes in der Zusammenfassunge enthalten sind.
            Stelle dabei aber sicher, dass Sinn und Inhalt des Originaltextes möglichst erhalten bleiben.
"""},
        {"role": "user", "content": f"""Hier ist der erste Text, fasse ihn zusammen: {original_text}"""}]
        
        prompt = self.pipeline.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )

        terminators = [
            self.pipeline.tokenizer.eos_token_id,
            self.pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]
        
        outputs = self.pipeline(
            prompt,
            max_new_tokens=100,
            eos_token_id=terminators,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
        )
        
        summary = outputs[0]["generated_text"][len(prompt):]
        return summary

    def _has_six_consecutive_words(self, original_text, summary):
        original_text_ngrams = set(ngrams(original_text.split(), 6))
        summary_ngrams = set(ngrams(summary.split(), 6))
        return bool(original_text_ngrams & summary_ngrams)
