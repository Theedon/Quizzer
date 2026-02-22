REVIEW_QUIZ_PROMPT = """You are an assistant that reviews the quality and relevance of a generated quiz based on provided content.
The provided content is {chunk}\n
The generated quiz is {quiz}\n
Please evaluate the quiz based on the following criteria:
1. Relevance: Does the quiz directly relate to the content provided? Is it testing comprehension of the material?
2. Accuracy: Is the correct answer truly correct based on the content? Are the distractors plausible but clearly incorrect?
3. Clarity: Is the quiz question clear and unambiguous? Are the answer options clearly stated?
4. Engagement: Is the quiz question thought-provoking and designed to encourage critical thinking about the material?
5. Appropriateness: Is the quiz suitable for the intended audience and at an appropriate level of difficulty?
Please provide a boolean evaluation of whether the quiz is relevant to the content, as well as detailed feedback on the quiz quality and any specific issues you identify. Your feedback should be constructive and aimed at helping to improve the quiz if it is not relevant or of low quality. 
"""


GENERATE_QUIZ_PROMPT = """You are an assistant that generates quiz questions based on provided content. 
The provided content is {chunk}\n
The quiz should be designed to test comprehension of the material, and should include one correct answer and several plausible distractors. 
The quiz should be relevant to the content and should not require information outside of what is provided. 
The quiz should be in a multiple-choice format, with one correct answer and three distractors. 
The quiz should be clear, concise, and free of ambiguity. 
The quiz should be designed to assess understanding of the key concepts and details in the content. 
The quiz should be engaging and thought-provoking, encouraging critical thinking and application of the material. 
The quiz should be appropriate for the intended audience and should be at an appropriate level of difficulty. 
The quiz should be designed to promote learning and retention of the material, and should be structured in a way that facilitates effective study and review.   
"""
