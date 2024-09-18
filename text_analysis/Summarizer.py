# -*- coding: utf-8 -*-
from ctransformers import AutoModelForCausalLM
from datasets import Dataset
import torch
import gc
from nltk import ngrams
from typing import List, Dict
from functools import lru_cache
from transformers import pipeline


# bartowski/Llama-3.1-SauerkrautLM-8b-Instruct-GGUF
# Llama-3.1-SauerkrautLM-8b-Instruct-Q6_K_L.gguf

class Summarizer:
    """A summarizer that uses a llama model to generate summaries."""
    
    def __init__(self, model_path: str = "TheBloke/em_german_leo_mistral-GGUF", 
                 model_file: str = "em_german_leo_mistral.Q6_K.gguf", 
                 max_new_tokens: int = 1024, 
                 context_length: int = 8192,
                 batch_size: int = 16,
                 fast_mode: bool = False,
                 fast_mode_model: str = "google/flan-t5-large"):
        self.max_new_tokens = max_new_tokens
        self.context_length = context_length
        self.batch_size = batch_size
        self.fast_mode = fast_mode

        if fast_mode:
            self.summarizer = pipeline("summarization", model=fast_mode_model, device=0 if torch.cuda.is_available() else -1)
        else:
            llm = AutoModelForCausalLM.from_pretrained(
                model_path,
                model_file=model_file,
                model_type="mistral",
                gpu_layers=32,  # Set to 0 for CPU-only, adjust if GPU is available
                context_length=context_length,
                threads=8  # Utilize multiple CPU threads
            )
            self.summarizer = lambda text: self._generate_summary(llm, text)

    def summarize(self, articles_list: List[Dict]) -> List[Dict]:
        """
        Generate summaries for each entry in the articles list and add them to the dataset.
        
        Parameters:
        articles_list (list): A list of dictionaries containing the articles.
        
        Returns:
        list: The original list of articles with an additional 'summary' field containing generated summaries.
        """
        dataset = Dataset.from_dict({"main_text": [article["main_text"] for article in articles_list]})

        def generate_summary(examples):
            summaries = []
            with torch.no_grad():
                for text in examples["main_text"]:
                    if self.fast_mode:
                        summary = self.summarizer(text, max_length=self.max_new_tokens, min_length=30, do_sample=False)[0]['summary_text']
                    else:
                        summary = self.summarizer(text)
                        while self._has_five_consecutive_words(text, summary):
                            summary = self.summarizer(text)
                    summaries.append(summary)
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            
            return {"summary": summaries}

        results = dataset.map(generate_summary, batched=True, batch_size=self.batch_size)

        # Update the original articles with the generated summaries
        for i, single_article_dict in enumerate(articles_list):
            single_article_dict["summary"] = results["summary"][i]

        # Memory cleanup
        del results
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

        return articles_list

    def _generate_summary(self, llm, original_text: str) -> str:
        truncated_text = self._truncate_text(original_text, self.context_length)
        prompt = self._create_prompt(truncated_text, fast_mode=False)
        
        summary = llm(prompt, max_new_tokens=self.max_new_tokens, temperature=0.7, top_k=50)
        return summary.split("ZUSAMMENFASSUNG:")[-1].strip()

    @staticmethod
    def _truncate_text(original_text: str, context_length: int) -> str:
        """Truncate the text based on context length."""
        words = original_text.split()
        if len(words) > context_length - 200:  # Leave room for prompt
            return ' '.join(words[:context_length - 200])
        return original_text

    def _create_prompt(self, truncated_text: str, fast_mode: bool) -> str:
        if fast_mode:
            return f"""Zusammenfassung des folgenden Textes. Achte darauf, dass sich nie mehr als 5 aufeinanderfolgende Wörter des Originaltextes wiederholen:

{truncated_text}

ZUSAMMENFASSUNG:"""
        else:
            return f'''Du bist ein präziser und hilfreicher deutscher KI-Text-Zusammenfasser. USER: Fasse den folgenden Text zusammen. Verwende dabei nie mehr als 5 aufeinanderfolgende Wörter des Originaltextes. Paraphrasiere und nutze Synonyme, um den Inhalt wiederzugeben, ohne direkt zu kopieren. Behalte den Sinn und die wichtigsten Informationen bei. Verzichte auf alle Formulierungen, die eine Zusammenfassung andeuten sollen, wie etwa "Dieser Text handelt von". Paraphrasiere einfach den Text in zusammenfassender Art.

TEXT ZUM ZUSAMMENFASSEN: {truncated_text} 

A: ZUSAMMENFASSUNG:'''

    @staticmethod
    def _has_five_consecutive_words(original_text: str, summary: str) -> bool:
        original_words = original_text.split()
        summary_words = summary.split()
        
        for i in range(len(summary_words) - 4):
            five_words = ' '.join(summary_words[i:i+5])
            if five_words in original_text:
                return True
        return False

