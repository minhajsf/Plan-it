import json
import os
from openai import OpenAI

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']


def generate_recommendations(movie_choices, preferences):
    print("\nProcessing request....")
    while True:
        try:
            client = OpenAI(
                api_key=OPENAI_API_KEY,
            )
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"Please give me a "
                                                  f"recommendation based on "
                                                  f"these movies here "
                                                  f"{movie_choices} "
                                                  f"and with the genres: "
                                                  f"{preferences}."},

                    {"role": "user", "content": "You are a movie recommendation bot that takes in similar movies "
                                                "and gives 30 specific movie recommendations as a response in a json format "
                                                "with the following keys: title, genre, rating out of 10 from IMDB, release date. "
                                                "Please provide the recommendations as one json string with the key 'recommendations' "
                                                "containing a list of 30 movies with their respective attributes. "
                                                "Use double quotes for all strings. Here is a sample format:\n\n"
                                                "{\n"
                                                "  \"recommendations\": [\n"
                                                "    {\n"
                                                "      \"title\": \"Movie Title\",\n"
                                                "      \"genre\": \"Genre\",\n"
                                                "      \"rating\": \"8.5\",\n"
                                                "      \"release_date\": \"YYYY-MM-DD\"\n"
                                                "    },\n"
                                                "    ... 29 more movies ...\n"
                                                "  ]\n"
                                                "}.\n"
                                                "Please end with a closing curly bracket."
                     }
                ]
            )
            return json.loads(completion.choices[0].message.content)
        except json.JSONDecodeError:
            print("There is a json decode error")


if __name__ == "__main__":
    generate_recommendations("Batman", "Action")