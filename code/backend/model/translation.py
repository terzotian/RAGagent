import asyncio
from typing import Literal, Union, List

# Use deep_translator instead of googletrans to avoid httpcore version conflicts
from deep_translator import GoogleTranslator

# Map internal language codes to deep_translator/Google API codes
LANG_MAP = {
    'zh-cn': 'zh-CN',
    'zh-tw': 'zh-TW',
    'en': 'en'
}

async def async_translate(text: Union[str, List[str]], target_language: Literal['en', 'zh-cn', 'zh-tw'] = 'en'):
    try:
        # Get correct language code
        target_lang = LANG_MAP.get(target_language.lower(), target_language)

        translator = GoogleTranslator(source='auto', target=target_lang)

        # Run sync translation in a thread to avoid blocking the event loop
        loop = asyncio.get_running_loop()

        if isinstance(text, str):
            result = await loop.run_in_executor(None, translator.translate, text)
            return result
        elif isinstance(text, list):
            # deep_translator has translate_batch
            result = await loop.run_in_executor(None, translator.translate_batch, text)
            return result

    except Exception as e:
        print(f"Translation error ({target_language}):", e)
        return text # Fallback to original text on error


if __name__ == "__main__":
    async def main():
        original_text = "我是岭南大学政策小助手"
        translated_text = await async_translate(original_text, "zh-tw")
        original_list = ["how about running", "請根據用戶問題和參考資料來回答"]
        translated_list = await async_translate(original_list, "zh-cn")
        print("original_text", original_text)
        print("translated_text", translated_text)
        print("original_list", original_list)
        print("translated_list", translated_list)

    asyncio.run(main())
