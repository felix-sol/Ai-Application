import os
import requests

class SAIAEmbeddings:
    def __init__(self, api_key):
        self.api_key = api_key
        self.endpoint = "https://chat-ai.academiccloud.de/v1/embeddings"
        self.model = "e5-mistral-7b-instruct"

    def embed_documents(self, texts):
        embeddings = []
        for text in texts:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": text,
                    "model": self.model,
                    "encoding_format": "float"
                }
            )
            response.raise_for_status()
            embeddings.append(response.json()['data'][0]['embedding'])
        return embeddings

    def embed_query(self, text):
        return self.embed_documents([text])[0]