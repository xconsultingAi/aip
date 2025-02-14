from prometheus_client import Counter, Histogram

class Monitoring:
    api_calls = Counter('llm_api_calls', 'API call count', ['model', 'status'])
    response_times = Histogram('llm_response_times', 'Response time histogram', ['model'])
    tokens_used = Counter('llm_tokens_used', 'Tokens used', ['model', 'type'])

    @classmethod
    def track_usage(cls, model: str, prompt_tokens: int, completion_tokens: int):
        cls.tokens_used.labels(model, 'prompt').inc(prompt_tokens)
        cls.tokens_used.labels(model, 'completion').inc(completion_tokens)