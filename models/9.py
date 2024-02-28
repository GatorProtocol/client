from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import json

def infer(prompt, entropy):
	analyzer = SentimentIntensityAnalyzer()
	scores = analyzer.polarity_scores(str(prompt))
	print(scores)
	return json.dumps(scores)