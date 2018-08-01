#!/usr/bin/python

# Usage example:
# python comments.py --videoid='<video_id>' --text='<text>'

import httplib2
import os
import sys
import time
import argparse

from google.cloud import language
from google.cloud.language import enums
from google.cloud.language import types

from apiclient.discovery import build_from_document
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains

# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "client_secrets.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
YOUTUBE_READ_WRITE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:
   %s
with information from the APIs Console
https://console.developers.google.com

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))
list_of_comments = []
sum_comments = 0
# Authorize the request and store authorization credentials.
def get_authenticated_service(args):
  flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=YOUTUBE_READ_WRITE_SSL_SCOPE,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("%s-oauth2.json" % sys.argv[0])
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, args)

  # Trusted testers can download this discovery document from the developers page
  # and it should be in the same directory with the code.
  with open("youtube-v3-discoverydocument.json", "r") as f:
    doc = f.read()
    return build_from_document(doc, http=credentials.authorize(httplib2.Http()))


# Call the API's commentThreads.list method to list the existing comment threads.
def get_comment_threads(youtube, video_id, gather_replies):
  count = 0
  page_token = ""

  while True:
    if page_token == "":
      results = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        textFormat="plainText",
        maxResults="75",
      ).execute()

    else: 
      results = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        textFormat="plainText",
        maxResults="75",
        pageToken = page_token
      ).execute()

    for item in results["items"]:
      count += 1
      comment = item["snippet"]["topLevelComment"]
      author = comment["snippet"]["authorDisplayName"]
      text = comment["snippet"]["textDisplay"]
      reply_count = item["snippet"]["totalReplyCount"]
      comment_id = comment["id"]
      #print comment_id
      if gather_replies and reply_count > 0:
        get_comments(youtube, comment_id)
      list_of_comments.append(text)
      #print "Comment %s by %s: %s" % (count, author, text)

    if "nextPageToken" in results:
      page_token = results["nextPageToken"]
    else: 
      break

  #print results["items"]
  return results["items"]


# Call the API's comments.list method to list the existing comment replies.
def get_comments(youtube, parent_id):
  results = youtube.comments().list(
    part="snippet",
    parentId=parent_id,
    textFormat="plainText"
  ).execute()

  for item in results["items"]:
    author = item["snippet"]["authorDisplayName"]
    text = item["snippet"]["textDisplay"]
    list_of_comments.append(text)

  return results["items"]


# Call the API's comments.insert method to reply to a comment.
# (If the intention is to create a new to-level comment, commentThreads.insert
# method should be used instead.)
def insert_comment(youtube, parent_id, text):
  insert_result = youtube.comments().insert(
    part="snippet",
    body=dict(
      snippet=dict(
        parentId=parent_id,
        textOriginal=text
      )
    )
  ).execute()

  author = insert_result["snippet"]["authorDisplayName"]
  text = insert_result["snippet"]["textDisplay"]
  print "Replied to a comment for %s: %s" % (author, text)


# Call the API's comments.update method to update an existing comment.
def update_comment(youtube, comment):
  comment["snippet"]["textOriginal"] = 'updated'
  update_result = youtube.comments().update(
    part="snippet",
    body=comment
  ).execute()

  author = update_result["snippet"]["authorDisplayName"]
  text = update_result["snippet"]["textDisplay"]
  print "Updated comment for %s: %s" % (author, text)


# Call the API's comments.setModerationStatus method to set moderation status of an
# existing comment.
def set_moderation_status(youtube, comment):
  youtube.comments().setModerationStatus(
    id=comment["id"],
    moderationStatus="published"
  ).execute()

  print "%s moderated succesfully" % (comment["id"])


# Call the API's comments.markAsSpam method to mark an existing comment as spam.
def mark_as_spam(youtube, comment):
  youtube.comments().markAsSpam(
    id=comment["id"]
  ).execute()

  print "%s marked as spam succesfully" % (comment["id"])


# Call the API's comments.delete method to delete an existing comment.
def delete_comment(youtube, comment):
  youtube.comments().delete(
    id=comment["id"]
  ).execute()

  print "%s deleted succesfully" % (comment["id"])

def print_result(annotations):
    score = annotations.document_sentiment.score
    magnitude = annotations.document_sentiment.magnitude

    for index, sentence in enumerate(annotations.sentences):
        sentence_sentiment = sentence.sentiment.score
        print('Sentence {} has a sentiment score of {}'.format(
            index, sentence_sentiment))

    print('Overall Sentiment: score of {} with magnitude of {}'.format(
        score, magnitude))
    return 0


def analyze(movie_review_filename):
    """Run a sentiment analysis request on text within a passed filename."""
    client = language.LanguageServiceClient()

    with open(movie_review_filename, 'r') as review_file:
        # Instantiates a plain text document.
        content = review_file.read()

    document = types.Document(
        content=content,
        type=enums.Document.Type.PLAIN_TEXT)
    annotations = client.analyze_sentiment(document=document)

    # Print the results
    print_result(annotations)

if __name__ == "__main__":
  """
  parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument(
    'movie_review_filename',
    help='The filename of the movie review you\'d like to analyze.')
  args = parser.parse_args()
  analyze(args.movie_review_filename)

  """
  # Instantiates a client``
  client = language.LanguageServiceClient()

  # The text to analyze
  
  argparser.add_argument("--videoid",
    help="Required; ID for video for which the comment will be inserted.")
  # The "text" option specifies the text that will be used as comment.
  #argparser.add_argument("--text", help="Required; text that will be used as comment.")
  args = argparser.parse_args()
  
  
  if not args.videoid:
    exit("Please specify videoid using the --videoid= parameter.")

  youtube = get_authenticated_service(args)



  #Can be used as an example of how to gather comments

  start_iter = time.time()
  video_comment_threads = get_comment_threads(youtube, args.videoid, True)
  end_iter = time.time()
  print list_of_comments
  print len(list_of_comments)
  print "Iterative method used {} seconds".format(end_iter - start_iter)
  #parent_id = video_comment_threads[0]["id"]
  #parent_id2 = video_comment_threads[1]["id"]
  sentiment_sum = 0 
  total_comments = len(list_of_comments)
  for item in list_of_comments:

    text = item
    document = types.Document(
        content=text,
        type=enums.Document.Type.PLAIN_TEXT)

    # Detects the sentiment of the text
    sentiment = client.analyze_sentiment(document=document).document_sentiment

    #print('Text: {}'.format(text))
    sentiment_value = sentiment.score * sentiment.magnitude
    print('Sentiment: {}, {}'.format(sentiment.score, sentiment.magnitude))
    sentiment_sum += sentiment_value
  print "Average positivity of the comments in this video is: {}".format(sentiment_sum / total_comments)

  """
  for num in range(len(video_comment_threads) - 1):
    print "HERE IS AN INDEX WITH VALUES IN IT: {}".format(num)
    parent_id = video_comment_threads[num]["id"]
    video_comments = get_comments(youtube, parent_id)
  """
  
  #video_comments = get_comments(youtube, parent_id)


"""
def get_comment_threads(youtube, video_id, page_token, gather_replies):
  
  if page_token == "":
    results = youtube.commentThreads().list(
      part="snippet",
      videoId=video_id,
      textFormat="plainText",
      maxResults="75",
    ).execute()

  else: 
    results = youtube.commentThreads().list(
      part="snippet",
      videoId=video_id,
      textFormat="plainText",
      maxResults="75",
      pageToken = page_token
    ).execute()
  count = 0
  
  for item in results["items"]:
    count += 1
    comment = item["snippet"]["topLevelComment"]
    author = comment["snippet"]["authorDisplayName"]
    text = comment["snippet"]["textDisplay"]
    reply_count = item["snippet"]["totalReplyCount"]
    comment_id = comment["id"]
    #print comment_id
    if gather_replies and reply_count > 0:
      get_comments(youtube, comment_id)
    list_of_comments.append(text)
    #print "Comment %s by %s: %s" % (count, author, text)
  if "nextPageToken" in results:
    get_comment_threads(youtube, video_id, results["nextPageToken"], gather_replies)

  #print results["items"]
  return results["items"]
"""