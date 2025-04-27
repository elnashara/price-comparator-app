import streamlit as st
import requests
from serpapi import GoogleSearch
import pandas as pd  # Needed for building a DataFrame

class PriceComparator:
    def __init__(self):
        self.hf_token = st.secrets['HF_TOKEN']
        self.serpapi_key = st.secrets['SERPAPI_KEY']

    def normalize_query_with_llm(self, query):
        api_url = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        payload = {"inputs": f"Normalize this product search: {query}"}
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            if response.ok:
                return response.json()[0]['generated_text']
        except Exception as e:
            print("LLM Error:", e)
        return query

    def serpapi_search(self, query, site):
        params = {
            "engine": "google",
            "q": f"{query} site:{site}",
            "api_key": self.serpapi_key
        }
        try:
            search = GoogleSearch(params)
            results = search.get_dict()

            if "shopping_results" in results and results["shopping_results"]:
                item = results["shopping_results"][0]
                price = item.get("price", "N/A")
                shipping = item.get("shipping", "N/A")
                total_cost = self.calculate_total_cost(price, shipping)

                return {
                    "Platform": site.split('.')[0].capitalize(),
                    "Title": item.get("title", "N/A"),
                    "Price": price,
                    "Shipping": shipping,
                    "Total Cost": total_cost,
                    "URL": item.get("link", "N/A")
                }

            for result in results.get("organic_results", []):
                title = result.get("title", "N/A")
                url = result.get("link", "N/A")
                detected = result.get("rich_snippet", {}).get("bottom", {}).get("detected_extensions", {})

                price = "N/A"
                shipping = "N/A"

                if "price" in detected:
                    price = f"${detected['price']}"
                elif "price_from" in detected and "price_to" in detected:
                    price = f"${detected['price_from']} - ${detected['price_to']}"

                if "shipping" in detected:
                    shipping = f"${detected['shipping']}"

                total_cost = self.calculate_total_cost(price, shipping)

                if price != "N/A":
                    return {
                        "Platform": site.split('.')[0].capitalize(),
                        "Title": title,
                        "Price": price,
                        "Shipping": shipping,
                        "Total Cost": total_cost,
                        "URL": url
                    }

            return None
        except Exception as e:
            print(f"Error searching {site}: {e}")
            return None

    def calculate_total_cost(self, price, shipping):
        """Helper to calculate total cost."""
        try:
            price_val = float(price.replace('$', '').replace(',', '').strip()) if isinstance(price, str) else 0.0
            shipping_val = 0.0
            if isinstance(shipping, str) and '$' in shipping:
                shipping_val = float(shipping.replace('$', '').replace(',', '').strip())
            return f"${price_val + shipping_val:.2f}"
        except Exception as e:
            print(f"Total cost calculation error: {e}")
            return "N/A"

    def search_amazon(self, query):
        return self.serpapi_search(query, "amazon.com")

    def search_walmart(self, query):
        return self.serpapi_search(query, "walmart.com")

    def search_ebay(self, query):
        return self.serpapi_search(query, "ebay.com")

    def run(self):
        st.title("🛒 Multi-Channel Price Comparator (Amazon, Walmart, eBay)")

        item_title = st.text_input("Item Title")
        upc = st.text_input("UPC")
        asin = st.text_input("ASIN")
        ean_gtin = st.text_input("EAN/GTIN")
        use_llm = st.checkbox("Normalize Query with Free LLM (HuggingFace)", value=False)

        if st.button("Search & Compare"):
            query = item_title or upc or asin or ean_gtin
            st.write(f"🔍 Searching for: `{query}`")

            if use_llm:
                query = self.normalize_query_with_llm(query)
                st.write(f"🧠 Normalized Query: `{query}`")

            # Perform searches
            amazon = self.search_amazon(query)
            walmart = self.search_walmart(query)
            ebay = self.search_ebay(query)

            # Collect results into a list
            results = [res for res in [amazon, walmart, ebay] if res]

            if results:
                # Convert to DataFrame
                df = pd.DataFrame(results)

                # Convert URL to clickable hyperlink
                df['URL'] = df['URL'].apply(lambda x: f"[Link]({x})" if x != "N/A" else "-")

                # Display a table with clickable hyperlinks
                st.markdown("### 💵 Price Comparison Table")
                st.markdown(
                    df.to_markdown(index=False),
                    unsafe_allow_html=True
                )
            else:
                st.warning("No results found!")

