import io
import requests
import pandas as pd
import streamlit as st
from serpapi import GoogleSearch
from datetime import datetime

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
            "api_key": self.serpapi_key,
            "no_cache": True  # <-- Force fresh results
        }
        try:
            search = GoogleSearch(params)
            results = search.get_dict()

            # # 🚨 DEBUG: Show raw response to help troubleshooting
            # st.subheader(f"🔍 Raw SerpAPI Results for {site}")
            # st.json(results)  # Show full JSON in Streamlit

            # Step 1: Check Shopping Results
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

            # Step 2: Try rich snippet in organic results
            for result in results.get("organic_results", []):
                url = result.get("link", "")
                if site not in url:
                    continue

                title = result.get("title", "N/A")
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

                return {
                    "Platform": site.split('.')[0].capitalize(),
                    "Title": title,
                    "Price": price,
                    "Shipping": shipping,
                    "Total Cost": total_cost,
                    "URL": url
                }

            # Step 3: Fallback to first organic result with domain match
            for result in results.get("organic_results", []):
                url = result.get("link", "")
                if site in url:
                    return {
                        "Platform": site.split('.')[0].capitalize(),
                        "Title": result.get("title", "N/A"),
                        "Price": "N/A",
                        "Shipping": "N/A",
                        "Total Cost": "N/A",
                        "URL": url
                    }

            return None
        except Exception as e:
            st.error(f"Error searching {site}: {e}")
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

        # Initialize session state only once
        if 'updated_results' not in st.session_state:
            st.session_state['updated_results'] = []

        # Search & Compare button
        if st.button("Search & Compare"):
            query = item_title or upc or asin or ean_gtin
            st.write(f"🔍 Searching for: `{query}`")

            if use_llm:
                query = self.normalize_query_with_llm(query)
                st.write(f"🧠 Normalized Query: `{query}`")

            amazon = self.search_amazon(query)
            walmart = self.search_walmart(query)
            ebay = self.search_ebay(query)

            results = [res for res in [amazon, walmart, ebay] if res]

            if results:
                updated_results = []
                for i, res in enumerate(results):
                    updated_results.append({
                        "Platform": res['Platform'],
                        "Title": res['Title'],
                        "Price": res['Price'],
                        "Shipping": res['Shipping'],
                        "Total Cost": res['Total Cost'],
                        "URL": res['URL']
                    })
                # Save initial search to session state
                st.session_state['updated_results'] = updated_results

        # Show table if we have any results in session
        if st.session_state['updated_results']:
            st.markdown("### 💵 Price Comparison Table (Editable)")

            new_results = []
            for i, res in enumerate(st.session_state['updated_results']):
                cols = st.columns([1, 2, 1, 1, 1, 2])

                platform = res['Platform']
                title = res['Title']
                price = res['Price']
                shipping = res['Shipping']
                total_cost = res['Total Cost']
                url = res['URL']

                cols[0].markdown(platform)
                cols[1].markdown(title)
                new_price = cols[2].text_input(f"Price {i}", price, key=f"price_{i}")
                new_shipping = cols[3].text_input(f"Ship {i}", shipping, key=f"ship_{i}")
                new_total = self.calculate_total_cost(new_price, new_shipping)
                cols[4].markdown(new_total)
                cols[5].markdown(f"[Link]({url})")

                new_results.append({
                    "Platform": platform,
                    "Title": title,
                    "Price": new_price,
                    "Shipping": new_shipping,
                    "Total Cost": new_total,
                    "URL": url
                })

            # Update session state with edited values
            st.session_state['updated_results'] = new_results

            # Download CSV button with timestamped filename
            df = pd.DataFrame(st.session_state['updated_results'])
            csv = df.to_csv(index=False).encode('utf-8')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"price_comparison_{timestamp}.csv"

            st.download_button(
                label="📥 Save Updates and Download CSV",
                data=csv,
                file_name=filename,
                mime='text/csv'
            )

            # Add Reset button to clear the session only when clicked
            if st.button("🔄 Reset Table"):
                st.session_state['updated_results'] = []

        else:
            st.info("🔍 Please perform a search to display and edit results.")
