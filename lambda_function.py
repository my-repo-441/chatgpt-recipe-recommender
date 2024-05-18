# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (AbstractRequestHandler, AbstractRequestInterceptor, AbstractExceptionHandler)
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.interfaces.audioplayer import AudioItem, Stream, PlayDirective, PlayBehavior

import gettext
import logging
import os
from openai import OpenAI
#import requests
from io import StringIO
import boto3
import json

client = OpenAI()
openai_key = os.getenv('OPENAI_API_KEY')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]

        speak_output = "どんなレシピが欲しい？"
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = "ハイ"

        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class ChatGPTImageGeneIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ChatGPTImageGeneIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        question = slots["question"].value
 
        prompt = question
                
        messages = [
            {
                "role": "system",
                "content": ("あなたはユーザーの希望を元に、栄養バランスの取れた献立とそのレシピを提案してくれます。"
                            "例えば、晩御飯の献立の場合、晩御飯に適して献立を考えて提案してくれます"
                            "必ず次のように最初に料理名：「○○○○、○○○○」という形式で献立の料理名を列挙して。"
                            "料理名：「白ごはん、チーズインハンバーグ、ポテトサラダ」"
                            "その後に、それぞれの料理の材料や作り方など必要なレシピを示して。")
            },
            {
                "role": "user",
                "content": prompt,
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            max_tokens=2000
        )
        
        answer = response.choices[0].message.content
        print(answer)
        
        # 料理名を切り取る
        start = answer.find("「") + 1
        end = answer.find("」")
        
        dish_names = answer[start:end]
        
        # Print the extracted dish names
        print(f"dish_name={dish_names}")
        
        # Use the extracted text as a prompt for image generation
        prompt_img = f"次の料理名の美味しそうな写真: {dish_names}"
        
        response = client.images.generate(
            model="dall-e-3",
            prompt = prompt_img, 
            #size="1024x1024",
            size="1792x1024",
            quality="standard",
            n=1,
        )
        
        
        image_url = response.data[0].url
        print(image_url)
    
        # SNSメッセージの組み立てとパブリッシュ
        message_to_publish = {
            "Recipe": answer,
            "Image URL": image_url,
            "Prompt": prompt_img
        }
        
        # message_json_to_publish = json.dumps(message_to_publish, ensure_ascii=False, indent=4)
            

        # JSON形式のメッセージを文字列に変換してフォーマット
        recipe_text = message_to_publish["Recipe"].replace("\\n", "\n")
        image_url_text = message_to_publish["Image URL"]
        prompt_text = message_to_publish["Prompt"]
        
        message_json_to_publish = f"Recipe:\n{recipe_text}\n\nImage URL:\n{image_url_text}\n\nPrompt:\n{prompt_text}"
        
        # SNSクライアントの作成
        sns_client = boto3.client('sns')
        
        # SNSトピックのARN
        topic_arn = 'arn:aws:sns:us-east-1:726788541449:OpenAI-Image-Generation'
        
        # SNSトピックにメッセージをパブリッシュ
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=message_json_to_publish,
            Subject='Generated Image URL'
        )
    


        speak_output = "提案したよ。"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask("他に質問はありますか？")
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = "どうしましたか？"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = "さようなら"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure."
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "ういいい"

        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = "例外です。"

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


class LocalizationInterceptor(AbstractRequestInterceptor):
    """
    Add function to request attributes, that can load locale specific data
    """

    def process(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        i18n = gettext.translation(
            'data', localedir='locales', languages=[locale], fallback=True)
        handler_input.attributes_manager.request_attributes["_"] = i18n.gettext

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(ChatGPTImageGeneIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler())

sb.add_global_request_interceptor(LocalizationInterceptor())

sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
