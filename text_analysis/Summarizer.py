# -*- coding: utf-8 -*-
from ctransformers import AutoModelForCausalLM
from datasets import Dataset
import torch
import gc
from nltk import ngrams

# TheBloke/em_german_mistral_v01-GPTQ --> for GPU inference
# TheBloke/em_german_mistral_v01-GGUF --> for CPU inference
# VAGOsolutions/Llama-3-SauerkrautLM-8b-Instruct --> German Llama
# Aleph-Alpha/Pharia-1-LLM-7B-control
#em_german_leo_mistral.Q4_K_M.gguf

class Summarizer:
    """A summarizer that uses a llama model to generate summaries."""
    def __init__(self, model_path="TheBloke/em_german_leo_mistral-GGUF", 
                 model_file="em_german_leo_mistral.Q2_K.gguf", 
                 max_new_tokens=200, 
                 context_length=8192):
        self.llm = AutoModelForCausalLM.from_pretrained(
            model_path,
            model_file=model_file,
            model_type="mistral",
            gpu_layers=0,  # Set to 0 for CPU-only, adjust if GPU is available
            context_length=context_length
        )
        self.max_new_tokens = max_new_tokens
        self.context_length = context_length

    def summarize(self, articles_list):
        """
        Generate summaries for each entry in the articles list and add them to the dataset.
        
        Parameters:
        articles_list (list): A list of dictionaries containing the articles.
        
        Returns:
        list: The original list of articles with an additional 'summary' field containing generated summaries.
        """
        
        # Convert articles_list to a Hugging Face Dataset
        dataset = Dataset.from_dict({"main_text": [article["main_text"] for article in articles_list]})

        # Define a function to generate summaries
        def generate_summary(example):
            with torch.no_grad():
                summary = self._generate_summary(example["main_text"])
                
                # Ensure no 5 consecutive words from the original text appear in the summary
                while self._has_five_consecutive_words(example["main_text"], summary):
                    summary = self._generate_summary(example["main_text"])
            
            # Clear CUDA cache after each summary generation
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            return {"summary": summary}

        # Apply the summarization to the entire dataset
        results = dataset.map(generate_summary, batched=False)

        # Update the original articles with the generated summaries
        for i, single_article_dict in enumerate(articles_list):
            single_article_dict["summary"] = results[i]["summary"]

        # Final memory cleanup
        del results
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

        return articles_list

    def _generate_summary(self, original_text):
        # Truncate or split the text if it's too long
        if len(original_text.split()) > self.context_length - 200:  # Leave room for prompt
            original_text = ' '.join(original_text.split()[:self.context_length - 200])

        prompt_template = f'''[INST] <<SYS>>
Du bist ein präziser und hilfreicher deutscher KI-Text-Zusammenfasser. 
Fasse den folgenden Nachrichtentext zusammen. Verwende dabei nie mehr als 5 aufeinanderfolgende Wörter des Originaltextes. 
Paraphrasiere und nutze Synonyme, um den Inhalt wiederzugeben, ohne direkt zu kopieren. 
Behalte den Sinn und die wichtigsten Informationen bei.
<</SYS>>
TEXT ZUM ZUSAMMENFASSEN: {original_text} 
ZUSAMMENFASSUNG:[/INST]
'''
        
        summary = self.llm(prompt_template, max_new_tokens=self.max_new_tokens)
        return summary.split("ZUSAMMENFASSUNG:")[-1].strip()

    def _has_five_consecutive_words(self, original_text, summary):
        original_words = original_text.split()
        summary_words = summary.split()
        
        original_5grams = set(ngrams(original_words, 5))
        summary_5grams = set(ngrams(summary_words, 5))
        
        return bool(original_5grams & summary_5grams)
