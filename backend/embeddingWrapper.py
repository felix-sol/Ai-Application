import os
import requests

# This class acts as a wrapper for the SAIA Embedding service, allowing easy integration with frameworks like LangChain:
class SAIAEmbeddings:
    # Constructor for the SAIAEmbeddings class.
    def __init__(self, api_key):
        self.api_key = api_key # Store the API key.
        self.endpoint = "https://chat-ai.academiccloud.de/v1/embeddings" # Define the API endpoint for the SAIA Embedding service.       
        self.model = "e5-mistral-7b-instruct" # Define the specific embedding model.

    # Method to generate embeddings for a list of text documents:
    def embed_documents(self, texts):
        embeddings = []
        # Iterate through each text document in the provided list.
        for text in texts:
            # Send a POST request to the SAIA Embedding service endpoint.
            response = requests.post(
                self.endpoint,
                # Set the necessary headers for authentication and content type.
                headers={
                    "Authorization": f"Bearer {self.api_key}", # API key for authentication.
                    "Content-Type": "application/json" # Indicate JSON request body.
                },
                # Provide the JSON payload with the input text, model, and encoding format.
                json={
                    "input": text,
                    "model": self.model,
                    "encoding_format": "float" # Request embeddings as float numbers.
                }
            )
            # Raise an HTTPError for bad responses.
            response.raise_for_status()
            embeddings.append(response.json()['data'][0]['embedding']) # 'data[0]['embedding']' is specific to the SAIA API response.
        # Return the list of all generated embeddings.
        return embeddings


    # Method to generate an embedding for a single text query:
    def embed_query(self, text):
        # Reuse the embed_documents method by passing the single text in a list. Then return the first (and only) embedding from the result list.
        return self.embed_documents([text])[0]