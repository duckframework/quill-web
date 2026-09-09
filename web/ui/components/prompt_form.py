"""
PromptForm component — left panel of Quill.

In normal mode: all fields active, real AI generation.
In demo mode: prompt textarea and example chips are disabled,
model selector is hidden, only design type selector is active.
"""
from duck.html.components import ForceUpdate
from duck.html.components.container import FlexContainer, Container
from duck.html.components.form import Form
from duck.html.components.heading import Heading
from duck.html.components.paragraph import Paragraph
from duck.html.components.label import Label
from duck.html.components.button import RaisedButton
from duck.html.components.select import Select, Option
from duck.html.components.textarea import TextArea
from duck.html.components.modal import Modal
from duck.html.components.link import Link
from duck.html.components.icon import Icon
from duck.html.components.span import Span
from duck.html.components import to_component

from duck.logging import logger
from duck.settings import SETTINGS

from web.ui.components.dummy_mode_banner import DummyModeBanner

# Quill Design Definitions
DESIGN_TYPES = [
    ("poster", "🎨  Poster / Flyer"),
    ("code", "💻  Code Snippet"),
    ("social", "📱  Social Media Card"),
    ("certificate",  "🏆  Certificate"),
    ("custom", "✦   Custom"),
    ("opengraph", "🌐  Open Graph Image"),
]

# One representative prompt per design type used in demo mode.
# Users never see these — the design type controls which one fires.
DEMO_PROMPTS = {
    "poster":      "A neon cyberpunk music festival poster",
    "code":        "Python quicksort algorithm, dark theme",
    "social":      "LinkedIn announcement — just launched my open source project",
    "certificate": "Certificate of completion for a Python web development course",
    "custom":      "A minimal motivational quote card",
    "opengraph":   "Open Graph image for a Python web framework called Duck Framework",
}

EXAMPLE_PROMPTS = [
    "A neon cyberpunk music festival poster",
    "Python quicksort algorithm, dark theme",
    "LinkedIn announcement card — new job",
    "Certificate of completion for Python course",
    "A minimal motivational quote card",
    "Open Graph image for my new SaaS product launch",
]

SELECT_STYLE = {
    "background": "rgba(255,255,255,0.05)",
    "border": "1px solid rgba(255,255,255,0.1)",
    "color": "#fff",
    "border-radius": "10px",
    "padding": "10px 12px",
    "font-size": "0.88rem",
    "width": "100%",
    "cursor": "pointer",
    "outline": "none",
}

SELECT_STYLE_DISABLED = {
    **SELECT_STYLE,
    "opacity": "0.35",
    "cursor": "not-allowed",
    "pointer-events": "none",
}

LABEL_STYLE = {
    "font-size": "0.72rem",
    "color": "rgba(255,255,255,0.4)",
    "text-transform": "uppercase",
    "letter-spacing": "0.08em",
}


class RateLimitModal(Modal):
    """
    Modal shown when a provider's rate limit is hit.
    """
    def show_rate_limit(self, provider: str, reset_time: str | None):
        """
        This populates the rate limit modal. Every time this is called, it first 
        resets the content of the modal.
        """
        self.set_content(self.build_content(provider, reset_time))
        self.modal_content.style.update({"max-width": "360px"})
        self.style["display"] = "flex"

    def show_insufficient_credits(self, provider: str):
        """
        This populates the rate limit modal with insufficient credits error message. 
        Every time this is called, it first resets the content of the modal.
        """
        content = self.build_content(provider, insufficient_credits=True)
        self.set_content(content)
        self.modal_content.style.update({"max-width": "360px"})
        self.style["display"] = "flex"

    def build_content(
        self,
        provider: str,
        reset_time: str | None = None,
        insufficient_credits: bool = False,
    ) -> FlexContainer:
        """
        Build and returns the content for the modal.
        
        Args:
            provider (str): The AI provider e.g., Anthropic, Groq, Gemini, etc
            reset_time (str | None): The reset tims for this provider.
            insufficient_credits (bool): Whether to show content related to insufficient AI credits.
        """
        from web.ui.pages.base import DONATE_URL
        
        heading = "Rate Limit Reached"
        provider_message = f"<strong>{provider}</strong> has reached its request limit."
        
        if insufficient_credits:
            heading = "Platform Credits Exhausted"
            provider_message = f"<strong>{provider}</strong> credits has been used up. We will refill if you choose to give to us. "
        
        # Update the model header text
        self.title_heading.text = heading
        
        # Create wrap/container
        wrap = FlexContainer()
        wrap.style.update({"flex-direction": "column", "gap": "14px", "padding": "8px 0"})
        
        # Configure title row
        title_row = FlexContainer()
        title_row.style.update({"flex-direction": "row", "align-items": "center", "gap": "10px"})
        
        # Configure icon
        icon = Span(text="⚠️", style={"font-size": "1.4rem"})
        
        # Configure the title heading
        title = Heading("h3", text=heading)
        title.style.update({"font-size": "1.05rem", "font-weight": "700", "color": "#fff", "margin": "0"})
        
        # Add title row children
        title_row.add_children([icon, title])
        
        # Configure the provider message
        provider_msg = Paragraph(
            inner_html=provider_message,
            style={
                "font-size": "0.85rem",
                "color": "rgba(255,255,255,0.65)",
                "margin": "0",
            },
        )
        
        # Add title row and provider message to the wrap/container
        wrap.add_children([title_row, provider_msg])
        
        # Configure reset time (if available)
        if reset_time:
            reset_box = Container(
                style={
                    "background": "rgba(99,102,241,0.1)",
                    "border": "1px solid rgba(99,102,241,0.25)",
                    "border-radius": "8px",
                    "padding": "10px 14px",
                },
            )
            reset_msg = Paragraph(
                inner_html=f"🕐 Limit resets in <strong>{reset_time}</strong>",
                style={"font-size": "0.82rem", "color": "#a5b4fc", "margin": "0"},
            )
            
            # Add reset message to reset_box and then add reset box to the wrap.
            reset_box.add_child(reset_msg)
            wrap.add_child(reset_box)

        # Add some suggestion
        suggestion = Paragraph(
            inner_html=(
                "💡 Try switching to a different model — each provider has its own separate limit. "
                "Or enable <strong>Demo Mode</strong> above to generate without any limits."
            ),
            style={
                "font-size": "0.82rem",
                "color": "rgba(255,255,255,0.55)",
                "margin": "0",
                "line-height": "1.5",
            },
        )
        
        # Configure some divider
        divider = Container(style={"height": "1px", "background": "rgba(255,255,255,0.07)", "width": "100%"})
        
        # Configure donate wrap
        donate_wrap = FlexContainer(style={"flex-direction": "column", "gap": "8px"})
        donate_msg = Paragraph(
            inner_html=(
                "Quill is free and costs real money to run. "
                "If it's useful to you, consider buying us a coffee ☕"
            ),
            style={
                "font-size": "0.8rem",
                "color": "rgba(255,255,255,0.45)",
                "margin": "0",
                "line-height": "1.5",
            },
        )
        donate_btn = Link(
            url=DONATE_URL,
            text="☕  Support Duck Framework",
            props={
                "target": "_blank",
                "rel": "noopener noreferrer",
            },
            style={
                "display": "inline-block", "background": "#FF5E5B", "color": "#fff",
                "padding": "9px 20px", "border-radius": "8px", "font-size": "0.85rem",
                "font-weight": "700", "text-decoration": "none", "width": "fit-content",
            },
        )
        donate_wrap.add_children([donate_msg, donate_btn])
        wrap.add_children([suggestion, divider, donate_wrap])
        return wrap


class PromptForm(Form):
    """
    Left-side prompt form.

    Renders differently based on demo mode state:
    - Demo OFF: All fields active, real AI generation
    - Demo ON:  Prompt disabled, chips hidden, model selector hidden,
                           design type controls which pre-built design streams
    """
    def on_create(self):
        super().on_create()
        self.style.update({
            "flex-direction": "column",
            "gap": "20px",
            "width": "100%",
            "flex-shrink": "0",
            "display": "flex",
        })
        self.build_header()
        self.build_dummy_banner()
        self.build_design_type_selector()
        self.build_model_selector()
        self.build_prompt_input()
        self.build_examples()
        self.build_submit_btn()
        self.build_rate_limit_modal()
        self.bind_form()
        self.apply_dummy_state()

    # Header
    def build_header(self):
        """
        Builds and adds header to the form
        """
        from web.ui.pages.base import GITHUB_URL
        
        title = Heading(
            "h1",
            text="Quill",
            style={
                "font-size": "1.8rem",
                "font-weight": "800",
                "letter-spacing": "-0.04em",
                "background": "linear-gradient(135deg, #fff 40%, rgba(255,255,255,0.4))",
                "-webkit-background-clip": "text",
                "-webkit-text-fill-color": "transparent",
                "background-clip": "text",
                "margin": "0",
            },
        )
        subtitle = Paragraph(
            inner_html="Describe a design. Get a pixel-perfect image.",
            style={
                "font-size": "0.82rem",
                "color": "rgba(255,255,255,0.35)",
                "margin": "0",
            },
         )
        
        # Github cta
        github_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-github" viewBox="0 0 16 16">'
            '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8"/>'
            '</svg>'
        )
        github_cta = Link(
            url=GITHUB_URL,
            klass="github-cta",
            props={
                "rel": "noopener noreferrer",
                "target": "_blank",
            },
            style={
                "display": "flex",
                "align-items": "center",
                "gap": "6px",
                "width": "fit-content",
            },
            children=[
                Paragraph(text="Available on Github"), Icon(inner_html=github_svg, style={"width": "16px", "height": "16px"}),
            ],
        )
        
        # Create header and add its children
        header = FlexContainer(style={"flex-direction": "column", "gap": "4px"})
        header.add_children([title, subtitle, github_cta])
        
        # Add header to the form
        self.add_child(header)

    # Demo mode banner
    def build_dummy_banner(self):
        # Pass self as the form reference so the banner can include
        # this form in update_targets when the toggle fires
        self.dummy_banner = DummyModeBanner(form=self)
        self.add_child(self.dummy_banner)

    # Design type selector
    def build_design_type_selector(self):
        """
        Builds and adds the `Design Type` selector/dropdown.
        """
        # Configure label
        lbl = Label(text="Design type", style=LABEL_STYLE)
        
        # Configure the select component
        self.type_select = Select(style=SELECT_STYLE)
        self.type_select.props["name"] = "design_type"
        
        for value, label in DESIGN_TYPES:
            opt = Option(text=label, props={"value": value})
            self.type_select.add_child(opt)

        # Configure type select group/container
        self.type_select_group = FlexContainer()
        self.type_select_group.style.update({"flex-direction": "column", "gap": "6px"})
        self.type_select_group.add_children([lbl, self.type_select])
        self.add_child(self.type_select_group)

    # Model selector
    def build_model_selector(self):
        """
        Builds and adds the `Model Type` selector/dropdown.
        """
        models = SETTINGS.get("QUILL_MODELS", [])
        lbl = Label(text="AI Model", style=LABEL_STYLE)
        
        # Configure the model select
        self.model_select = Select(style=SELECT_STYLE)
        self.model_select.props["name"] = "model_id"
        self.model_select.props["id"] = "quill-model-select"
        
        for i, (model_id, display, _) in enumerate(models):
            opt = Option(text=display, props={"value": model_id})
            
            if i == 0:
                opt.props["selected"] = "selected"
            
            # Add option
            self.model_select.add_child(opt)

        # Configure the free badge
        free_badge = to_component(
            "All models are free to use",
            "span",
            style={
                "font-size": "0.68rem", "color": "#4ade80",
                "background": "rgba(74,222,128,0.08)",
                "border": "1px solid rgba(74,222,128,0.2)",
                "padding": "2px 8px", "border-radius": "99px", "width": "fit-content",
            },
        )
        self.model_select_group = FlexContainer()
        self.model_select_group.id = "quill-model-group"
        self.model_select_group.style.update({"flex-direction": "column", "gap": "6px"})
        self.model_select_group.add_children([lbl, self.model_select, free_badge])
        self.add_child(self.model_select_group)

    # Prompt textarea
    def build_prompt_input(self):
        """
        Builds and adds the prompt textarea to the form.
        """
        self.prompt_lbl = Label(text="Your prompt", style=LABEL_STYLE)
        
        # Configure the prompt input.
        self.prompt_input = TextArea(
            id="quill-prompt",
            name="prompt",
            placeholder="e.g. A neon cyberpunk music festival poster for Lagos…",
            style={
                "background": "rgba(255,255,255,0.05)",
                "border": "1px solid rgba(255,255,255,0.1)",
                "color": "#fff", "border-radius": "10px",
                "padding": "12px 14px", "font-size": "0.88rem",
                "width": "100%", "resize": "vertical", "outline": "none",
                "font-family": "inherit", "line-height": "1.6", "min-height": "110px",
            },
            props={"rows": "5"},
        )
        
        # Configure and add prompt group
        self.prompt_group = FlexContainer(style={"flex-direction": "column", "gap": "6px"})
        self.prompt_group.add_children([self.prompt_lbl, self.prompt_input])
        self.add_child(self.prompt_group)

    # Example chips
    def build_examples(self):
        """
        Builds and adds example chips to the form.
        """
        lbl = Label(text="Try an example", style=LABEL_STYLE)
        
        # Configure chips wrap
        self.chips_wrap = FlexContainer(
            style={
                "flex-direction": "row",
                "flex-wrap": "wrap",
                "gap": "6px",
            },
         )
         
        for example in EXAMPLE_PROMPTS:
            chip = to_component(
                example,
                "button",
                props={
                    "type":"button",
                    "class":"quill-example-chip",
                    "onclick": f"document.getElementById('quill-prompt').value = '{example}'",
                },
                style={
                    "background": "rgba(255,255,255,0.04)",
                    "border": "1px solid rgba(255,255,255,0.08)",
                    "color": "rgba(255,255,255,0.5)", "border-radius": "99px",
                    "padding": "4px 10px", "font-size": "0.7rem",
                    "cursor": "pointer", "font-family": "inherit",
                    "text-align": "left", "line-height": "1.4",
                },
            )
            self.chips_wrap.add_child(chip)
        
        # Configure and add examples group.
        self.examples_group = FlexContainer()
        self.examples_group.style.update({"flex-direction": "column", "gap": "8px"})
        self.examples_group.add_children([lbl, self.chips_wrap])
        self.add_child(self.examples_group)

    # Submit button
    def build_submit_btn(self):
        """
        Builds the status strip (generating indicator + error message)
        and the submit button. The strip sits directly above the button.
        """
        # Status strip — hidden by default, shown during generation or on error
        status_strip = FlexContainer(
            id="quill-status-strip",
            style={
                "display": "none",
                "flex-direction": "row",
                "align-items": "center",
                "gap": "8px",
                "padding": "9px 14px",
                "border-radius": "8px",
                "font-size": "0.8rem",
                "line-height": "1.4",
            },
        )

        status_icon = to_component("", "span")
        status_icon.id = "quill-status-icon"

        status_text = to_component("", "span")
        status_text.id = "quill-status-text"
        status_text.style["flex"] = "1"

        status_strip.add_children([status_icon, status_text])
        self.add_child(status_strip)

        # Submit button
        self.submit_btn = RaisedButton(
            id="quill-submit-btn",
            text="✦  Generate Design",
            bg_color="#6366f1",
            color="#fff",
            props={
                "type": "submit",
            },
            style={
                "width": "100%", "padding": "13px", "border-radius": "10px",
                "font-size": "0.95rem", "font-weight": "700",
                "cursor": "pointer", "letter-spacing": "0.02em", "margin-top": "4px",
                "animation": "",
            },
        )
        self.add_child(self.submit_btn)

    # Rate limit modal
    def build_rate_limit_modal(self):
        """
        Builds and adds the rate limit modal.
        """
        self.rate_limit_modal = RateLimitModal(
            title="Rate Limit Reached",
            show_close=True,
            open_on_ready=False,
            style={
                "align-items": "center",
                "padding": "10px",
            },
        )
        self.rate_limit_modal.modal_content.style["padding"] = "10px"
        self.add_child(self.rate_limit_modal)

    # Apply dummy state to UI
    def apply_dummy_state(self):
        """
        Locks or unlocks fields based on current demo mode state.
        Called on first render and on every re-render (which happens
        when the toggle fires via update_self=True on the form bind).

        Demo ON:
        - Prompt textarea disabled and greyed out
        - Example chips visible but disabled (clicking does nothing)
        - Model selector hidden (not relevant in demo mode)
        - Button label changes to "⚡ Run Demo"

        Demo OFF (default / live mode):
        - All fields fully active
        - Button label is "✦ Generate Design"
        """
        is_dummy = self.dummy_banner.is_dummy_enabled()

        if is_dummy:
            # Disable prompt textarea
            self.prompt_input.props["disabled"] = "true"
            self.prompt_input.props.pop("required") if "required" in self.prompt_input.props else None
            self.prompt_input.style.update({
                "opacity": "0.35",
                "cursor": "not-allowed",
                "resize": "none",
            })
            
            # Hide model selector — irrelevant in demo mode
            self.model_select_group.style["display"] = "none"
            
            # Keep example chips visible but disable their onclick
            for chip in self.chips_wrap.children:
                chip.props["disabled"] = "true"
                chip.style.update({
                    "opacity": "0.35",
                    "cursor": "not-allowed",
                    "pointer-events": "none",
                })
            self.submit_btn.text = "⚡  Run Demo"
        else:
            # Restore prompt textarea
            self.prompt_input.props.pop("disabled") if "disabled" in self.prompt_input.props else None
            self.prompt_input.props["required"] = "true"
            self.prompt_input.style.update({
                "opacity": "1",
                "cursor": "text",
                "resize": "vertical",
            })
            
            # Show model selector
            self.model_select_group.style["display"] = "flex"
            
            # Restore example chips
            for chip in self.chips_wrap.children:
                chip.props.pop("disabled", None)  if "disabled" in chip.props else None
                chip.style.update({
                    "opacity": "1",
                    "cursor": "pointer",
                    "pointer-events": "auto",
                })
            self.submit_btn.text = "✦  Generate Design"

    #  Lively bind
    def bind_form(self):
        """
        Bind form `submit` event.
        """
        self.bind(
            "submit",
            self.handle_generate,
            update_targets=[self.rate_limit_modal],
            update_self=False,
        )

    # Handler
    async def handle_generate(self, source, event, form_inputs, ws):
        """
        Async Lively form `submit` handler.

        In demo mode: ignores the prompt input and uses a preset prompt
        matching the selected design type.
        In normal mode: uses the actual prompt and calls the real AI provider.
        """
        from web.ai_client import (
            stream_design,
            RateLimitError,
            MissingApiKeyError,
            InsufficientCreditsError,
       )

        design_type = (form_inputs.get("design_type", "custom") or "custom").strip()
        model_id = (form_inputs.get("model_id", "") or "").strip()
        use_dummy = self.dummy_banner.is_dummy_enabled()
        
        async def show_error(error_heading, error: str, error_description: str):
            """
            Shows an error to the client using JS.
            """
            await ws.execute_js(
                "document.getElementById('quill-generating-badge').style.display='none';"
                "var s=document.getElementById('quill-spinner-overlay'); if(s) s.style.display='none';",
                wait_for_result=False,
            )
            await ws.execute_js(
                f"quillSetStatusError('{error}');",
                wait_for_result=False,
            )
            await ws.execute_js(
                f"quillShowError('{error_heading}', '{error_description}');",
                wait_for_result=False,
            )
            
        def extract_full_html_document(content: str) -> str:
            """
            Extract a complete HTML document if present, preserving <head> and <body>.
        
            Removes any text before <!DOCTYPE>/<html> and after </html>.
        
            Args:
                content: Raw model output.
        
            Returns:
                Clean HTML document or original content if no document detected.
            """
            lower = content.lower()
        
            # Find start of document
            start = -1
            
            if "<!doctype" in lower:
                start = lower.find("<!doctype")
            elif "<html" in lower:
                start = lower.find("<html")
        
            if start == -1:
                return content.strip()
        
            # Find end of document
            end = lower.rfind("</html>")
            if end != -1:
                end += len("</html>")
                return content[start:end].strip()
        
            # Fallback: no closing tag
            return content[start:].strip()

        if use_dummy:
            # In demo mode the prompt is determined by design type
            prompt = DEMO_PROMPTS.get(design_type, DEMO_PROMPTS["custom"])
        
        else:
            # Get the provided prompt
            prompt = (form_inputs.get("prompt", "") or "").strip()
            
            # If no prompt is provided, show a visible error in the preview pane
            if not prompt:
                await ws.execute_js(
                    "quillShowError('Prompt required', 'Please enter a prompt describing the design you want.');",
                    wait_for_result=False,
                )
                return

        # Re-apply UI state in case form was re-rendered
        self.apply_dummy_state()
        
        # Disable the submit button and start the stream UI with the design type
        # so dimensions and hint message adapt to the chosen design
        # Show generating state on the status strip and disable the button
        await ws.execute_js(
            f"quillStartStream('{design_type}'); quillSetGenerating();"
            "document.getElementById('quill-submit-btn').disabled = true;",
            wait_for_result=True,
        )
        
        # Build and show html buffer chunk by chunk
        html_buffer = ""
        error = None
        
        try:
            async for chunk in stream_design(
                prompt,
                design_type,
                model_id,
                force_dummy=use_dummy,
            ):
                # Increment buffer and show the result immediately
                html_buffer += chunk
                safe = (
                    html_buffer
                    .replace("\\", "\\\\")
                    .replace("`", "\\`")
                    .replace("$", "\\$")
                )
                await ws.execute_js(
                    f"quillSetPreview(`{safe}`);",
                    wait_for_result=False,
                )

            # If AI was dumb enough to share its thougths, strip that here.
            html_buffer = extract_full_html_document(html_buffer)
            
            # Finalise the generated HTML content.
            safe_final = (
                html_buffer
                .replace("\\", "\\\\")
                .replace("`", "\\`")
                .replace("$", "\\$")
            )
            await ws.execute_js(f"quillFinalise(`{safe_final}`);", wait_for_result=True)
            
        except RateLimitError as e:
            reset_note = f" Resets in {e.reset_time}." if e.reset_time else ""
            error = f"{e.provider} rate limit reached.{reset_note} Try a different model or enable Demo Mode"
            error_heading = 'Rate Limit Reached'
            error_description = (
                f"'{e.provider} has reached its request limit."
                + reset_note
                + " Try a different model or enable Demo Mode."
            )
            
            # Preview the error
            await show_error(error_heading, error, error_description)
            
            # Also show the detailed rate limit modal
            self.rate_limit_modal.show_rate_limit(e.provider, e.reset_time)
            return ForceUpdate(self.rate_limit_modal, ["style"])
            
        except InsufficientCreditsError as e:
            error = f"{e.provider} credits exhausted. Try a different model or enable Demo Mode"
            error_heading = 'AI Credits exhausted'
            error_description = (
                f"'{e.provider} credits have been used up. "
                + " Try a different model or enable Demo Mode."
            )
            
            # Preview the error
            await show_error(error_heading, error, error_description)
            
            # Also show the detailed rate limit modal
            self.rate_limit_modal.show_insufficient_credits(e.provider)
            return ForceUpdate(self.rate_limit_modal, ["style"])

        except MissingApiKeyError as e:
            reason = "API Key is not set in settings. " if SETTINGS['DEBUG'] else ""
            error = f'{e.provider} is unavailable. {reason}Select a different model or enable Demo Mode.'
            error_heading = "Model Unavailable" if not SETTINGS['DEBUG'] else "Missing API Key"
            error_description = (
                f"Sorry, the {e.provider} model is currently unavailable. "
                f"Please select a different model or enable Demo Mode to try without one."
            )
            
            # Preview the error
            await show_error(error_heading, error, error_description)

        except Exception as e:
            error = "Something went wrong, please try again"
            error_heading = "Something went wrong"
            error_description = "An unexpected error occurred. Please try again"
            
            if SETTINGS["DEBUG"]:
                # Log the exception in debug mode
                logger.log_exception(e)
            
            # Preview the error
            await show_error(error_heading, error, error_description)
            
        finally:
            # Re-enable button and restore correct label for current mode
            # Force an update to sync all button props, style and inner_html to the client
            self.submit_btn.props.pop("disabled") if "disabled" in self.submit_btn.props else None
            
            # Enable button as ForceUpdate doesn't account for props not initially set e.g., disabled prop.
            await ws.execute_js(
                (
                    "const submitBtn = document.getElementById('quill-submit-btn');"
                    "submitBtn.disabled = false;"
                ),
                wait_for_result=True,
            )

            if not error:
                # Clear the generating indicator on success
                await ws.execute_js("quillClearStatus();", wait_for_result=False)

            # Return ForceUpdate to sync current changes on submit button to the client.
            if not html_buffer:
                # Maybe we got some error
                await ws.execute_js("quillSwitchTab('preview');")
            return ForceUpdate(self.submit_btn, ["all"])


# User agents available in import mode
USER_AGENTS = [
    ("desktop_chrome",   "Desktop — Chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
    ("desktop_firefox",  "Desktop — Firefox", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0"),
    ("desktop_safari",   "Desktop — Safari", "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"),
    ("iphone",  "Mobile — iPhone Safari",  "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1"),
    ("android",  "Mobile — Android Chrome", "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36"),
    ("googlebot", "Googlebot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("custom", "Custom…", ""),
]

# JS to show/hide the custom UA input
IMPORT_UA_SCRIPT = """
function quillToggleCustomUa() {
    var sel  = document.getElementById('quill-ua-select');
    var wrap = document.getElementById('quill-custom-ua-wrap');
    if (!wrap) return;
    wrap.style.display = (sel && sel.value === 'custom') ? 'flex' : 'none';
}
"""

from duck.html.components.script import Script
from duck.html.components.input import Input


class ImportForm(Form):
    """
    Import mode form — fetches an external URL server-side with a chosen
    user agent and streams the raw HTML into the preview panel.

    The user can pick from preset user agents (desktop, mobile, bot)
    or supply a fully custom UA string. The fetched page is streamed
    into the preview exactly like a generated design, so all the usual
    controls (resize sliders, download, code editor) work as normal.
    """
    def on_create(self):
        super().on_create()
        self.style.update({
            "flex-direction": "column",
            "gap": "20px",
            "width": "100%",
            "flex-shrink": "0",
            "display": "flex",
        })
        self.build_header()
        self.build_url_input()
        self.build_ua_selector()
        self.build_submit()
        self.bind_form()
        self.add_child(Script(inner_html=IMPORT_UA_SCRIPT))

    def build_header(self):
        """
        Header explaining what import mode does.
        """
        title = Heading(
            "h2",
            text="Import a Page",
            style={
                "font-size": "1.8rem",
                "font-weight": "800",
                "letter-spacing": "-0.04em",
                "background": "linear-gradient(135deg, #fff 40%, rgba(255,255,255,0.4))",
                "-webkit-background-clip": "text",
                "-webkit-text-fill-color": "transparent",
                "background-clip": "text",
                "margin": "0",
            },
        )
        sub = Paragraph(
            inner_html="Fetch any URL and preview it as a downloadable design.",
            style={"font-size": "0.82rem", "color": "rgba(255,255,255,0.35)", "margin": "4px 0 0"},
        )
        header = FlexContainer(style={"flex-direction": "column", "gap": "4px"})
        header.add_children([title, sub])
        self.add_child(header)

    def build_url_input(self):
        """
        URL input field.
        """
        lbl = Label(text="Page URL", style=LABEL_STYLE)
        self.url_input = Input(
            type="url",
            placeholder="https://example.com",
            style={
                "background": "rgba(255,255,255,0.05)",
                "border": "1px solid rgba(255,255,255,0.1)",
                "color": "#fff",
                "border-radius": "10px",
                "padding": "11px 14px",
                "font-size": "0.88rem",
                "width": "100%",
                "outline": "none",
                "font-family": "inherit",
            },
        )
        self.url_input.props["name"] = "import_url"
        self.url_input.props["id"]   = "quill-import-url"

        group = FlexContainer(style={"flex-direction": "column", "gap": "6px"})
        group.add_children([lbl, self.url_input])
        self.add_child(group)

    def build_ua_selector(self):
        """
        User agent selector — preset devices plus a custom text input.
        """
        lbl = Label(text="View as device", style=LABEL_STYLE)

        self.ua_select = Select(style=SELECT_STYLE)
        self.ua_select.props["name"]     = "user_agent_key"
        self.ua_select.props["id"]       = "quill-ua-select"
        self.ua_select.props["onchange"] = "quillToggleCustomUa()"

        for key, display, _ in USER_AGENTS:
            opt = Option(text=display, props={"value": key})
            if key == "desktop_chrome":
                opt.props["selected"] = "selected"
            self.ua_select.add_child(opt)

        # Custom UA text input — hidden unless "Custom…" is selected
        custom_wrap = FlexContainer(
            id="quill-custom-ua-wrap",
            style={"display": "none", "flex-direction": "column", "gap": "4px"},
        )
        custom_lbl = Label(
            text="Custom user agent string",
            style={**LABEL_STYLE, "margin-top": "4px"},
        )
        self.custom_ua_input = Input(
            type="text",
            placeholder="Mozilla/5.0 ...",
            style={
                "background": "rgba(255,255,255,0.05)",
                "border": "1px solid rgba(255,255,255,0.1)",
                "color": "#fff",
                "border-radius": "10px",
                "padding": "10px 14px",
                "font-size": "0.82rem",
                "width": "100%",
                "outline": "none",
                "font-family": "monospace",
            },
        )
        self.custom_ua_input.props["name"] = "custom_user_agent"
        custom_wrap.add_children([custom_lbl, self.custom_ua_input])

        group = FlexContainer(style={"flex-direction": "column", "gap": "6px"})
        group.add_children([lbl, self.ua_select, custom_wrap])
        self.add_child(group)

    def build_submit(self):
        """
        Status strip and fetch button.
        """
        # Status strip
        status_strip = FlexContainer(
            id="quill-import-status-strip",
            style={
                "display": "none",
                "flex-direction": "row",
                "align-items": "center",
                "gap": "8px",
                "padding": "9px 14px",
                "border-radius": "8px",
                "font-size": "0.8rem",
            },
        )
        s_icon = to_component("", "span")
        s_icon.id = "quill-import-status-icon"
        s_text = to_component("", "span")
        s_text.id = "quill-import-status-text"
        s_text.style["flex"] = "1"
        status_strip.add_children([s_icon, s_text])
        self.add_child(status_strip)

        # Fetch button
        self.import_btn = RaisedButton(
            id="quill-import-btn",
            text="⤓  Fetch & Preview",
            bg_color="#6366f1",
            color="#fff",
            props={"type": "submit"},
            style={
                "width": "100%", "padding": "13px", "border-radius": "10px",
                "font-size": "0.95rem", "font-weight": "700",
                "cursor": "pointer", "letter-spacing": "0.02em",
            },
        )
        self.add_child(self.import_btn)

    def bind_form(self):
        self.bind(
            "submit",
            self.handle_import,
            update_self=False,
        )

    async def handle_import(self, source, event, form_inputs, ws):
        """
        Fetches the given URL server-side using the selected user agent
        and streams the HTML into the preview panel.
        """
        from web.ui.pages.base import DONATE_URL
        
        raw_url  = (form_inputs.get("import_url", "") or "").strip()
        ua_key = (form_inputs.get("user_agent_key", "desktop_chrome") or "desktop_chrome").strip()
        custom_ua = (form_inputs.get("custom_user_agent", "") or "").strip()
        
        async def show_error(error_heading: str, description: str):
            """
            Execute JS code to preview the error.
            """
            await ws.execute_js(
                f"quillShowImportStatus(`error`, `&#9888; {description}.`);"
                f"quillShowError(`{error_heading}`, `{description}.`);"
                f"document.getElementById('quill-import-btn').disabled = false;",
                wait_for_result=False,
            )
            
        # NOTE: THIS FEATURE IS NOT SUPPORTED YET
        # This feature is causing some errors, it needs more time for implementation
        
        # Errors include:
        #     Blocked requests when loading external scripts from the fetched page
        #     External URLs (scripts/stylesheets) in fetched page are being treated as relative URLs and are being directed towards our server.
        
        # Just show an error that the feature is not implemented.
        await show_error(
            "Coming Soon",
            f"This feature is not supported yet. "
            f"For the time being, please <a href='{DONATE_URL}' target='_blank' rel='noreferrer noopener'>donate</a> so that we can fully support this feature."
        )
        return
        
        # Start processing here (when feature is fully supported)
        if not raw_url:
            await show_error("Fetch Failed", "Please enter a URL to fetch.")
            return
            
        if not raw_url.startswith(("http://", "https://")):
            raw_url = "https://" + raw_url

        # Resolve user agent string
        if ua_key == "custom":
            user_agent = custom_ua or "Mozilla/5.0"
        else:
            user_agent = next(
                (ua for key, _, ua in USER_AGENTS if key == ua_key),
                USER_AGENTS[0][2],
            )
            
        # Show spinner and disable button
        await ws.execute_js(
            f"quillStartStream('{ua_key if ua_key != 'custom' else 'ua_custom'}');"
            "quillShowImportStatus('loading', '&#9711; Fetching page...');"
            "document.getElementById('quill-import-btn').disabled = true;",
            wait_for_result=True,
        )

        try:
            # Make a request to the provided URL.
            # Use Async API here for request making
            # Cap at 1MB to avoid huge pages
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "identity",
            }
            
        except Exception:
            await show_error("Fetch Failed", "'Something went wrong. The site may block external fetches.")
            return
            
        # Stream HTML into preview in chunks (if necessary, same concept like what's being done in PromptForm.handle_generate may apply here')
        # Or just preview the whole page at once to avoid external URLs being treated as relative URLs
        