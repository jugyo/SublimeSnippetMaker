import os
import glob

import sublime
import sublime_plugin

template = """<snippet>
<!--
    The text to insert into the document when the snippet it applied.
    Supports snippet fields and variables.

    # Fields
    Snippets support fields, locations within the snippet that the user may
    Tab through after inserting the snippet. Fields may be simple positions,
    but may also provide default content.

    Field formats:
        - "$N"
        - "${N:TEXT}"

    "N" is an integer representing the Nth field in the snippet, and
    "TEXT" is default text to place in the field.

    If a snippet does not contain field $0, it is implicitly added at the end.

    # Variables
    The following variables may be added to a snippet to include information
    from the file the snippet is being inserted into:
        - "$SELECTION": The current selection.
        - "$TM_SELECTED_TEXT": The current selection.
        - "$TM_LINE_INDEX": The 0-based line number of the current line.
        - "$TM_LINE_NUMBER": The 1-based line number of the current line.
        - "$TM_DIRECTORY": The path to the directory containing the file.
        - "$TM_FILEPATH": The path to the file.
        - "$TM_FILENAME": The file name of the file.
        - "$TM_CURRENT_WORD": The contents of the current word.
        - "$TM_CURRENT_LINE": The contents of the current line.
        - "$TM_TAB_SIZE": The number of spaces per tab.
        - "$TM_SOFT_TABS": YES or NO – if tabs should be translated to spaces.
        - "$TM_SCOPE": The base scope name of the file’s syntax.

    In addition to the named variables above, fields may also be used as
    variables, allowing a user to enter a single value and have it repeated in
    multiple places. For example, "${3:$1}" will use the value of field 1 in
    field 3.

    # Variable Substitution
    Variables can be directly referenced, or they may be modified using a
    regular expression. Variables with substitutions are written in the format
    "${name/regex/replace/flags}".

    The regex segment supports regular expressions, while the replace segment
    supports a corresponding replace format. The flags segment can contain
    zero or more letters from the following list:
        - "g": All occurrences, rather than just the first, should be replaced.
        - "i": Case insensitive matching should be performed.
        - "m": Multiline mode, where "^" matches the beginning of each line.

    # Escaping
    Since snippets can contain variables, which start with a "$", literal "$"
    characters must be written as "\$".

    When performing variable substitution, literal "/" characters must be escaped
    by prefixing them with a backslash.
-->
<content><![CDATA[
%s
]]></content>

<!-- The text used to match the snippet in the completions popup -->
<tabTrigger>%s</tabTrigger>

<!-- An optional description of the snippet, which is shown in the Command Palette. -->
<description>%s</description>

<!-- The selector of the syntax the snippet should be enabled for -->
<scope>%s</scope>
</snippet>"""


def get_snippets():
    settings = sublime.load_settings('SnippetMaker.sublime-settings')
    location = settings.get('snippet_location', 'Snippets')
    snippets = [
        [os.path.basename(filepath), filepath] for filepath in glob.iglob(
            os.path.join(
                sublime.packages_path(),
                'User',
                location,
                '*.sublime-snippet'
            )
        )
    ]
    return snippets


class MakeSnippetCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        settings = sublime.load_settings('SnippetMaker.sublime-settings')
        should_escape_dollar_sign = settings.get('always_escape_dollar_sign', True)

        self.snippet_text = "\n".join(
            [self.view.substr(i) for i in self.view.sel()]
        )

        if should_escape_dollar_sign:
            self.snippet_text = self.snippet_text.replace('$', '\\$')

        sublime.active_window().show_input_panel(
            'Trigger',
            '',
            self.set_trigger,
            None,
            None
        )

    def set_trigger(self, trigger):
        self.trigger = trigger
        sublime.active_window().show_input_panel(
            'Description',
            '',
            self.set_description,
            None,
            None
        )

    def set_description(self, description):
        self.description = description
        scopes = self.view.scope_name(
            self.view.sel()[0].begin()
        ).strip().replace(' ', ', ')
        sublime.active_window().show_input_panel(
            'Scope',
            scopes,
            self.set_scopes,
            None,
            None
        )

    def set_scopes(self, scopes):
        self.scopes = scopes
        self.ask_file_name()

    def ask_file_name(self):
        sublime.active_window().show_input_panel(
            'File Name',
            self.trigger + '.sublime-snippet',
            self.make_snippet,
            None,
            None
        )

    def make_snippet(self, file_name):
        settings = sublime.load_settings('SnippetMaker.sublime-settings')
        location = settings.get('snippet_location', 'Snippets')

        file_path = os.path.join(
            sublime.packages_path(),
            'User',
            location,
            file_name
        )

        dir_path = os.path.join(
            sublime.packages_path(),
            'User',
            location
        )
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        if os.path.exists(file_path) and not sublime.ok_cancel_dialog(
            'Override %s?' % file_name
        ):
            self.ask_file_name()
            return

        try:
            self.write_snippet(file_path)
        except OSError:
            sublime.error_message('Please specify a valid file name, i.e. `awesome.sublime-snippet`')  # noqa: E501
            self.ask_file_name()
        else:
            sublime.active_window().open_file(file_path)

    def write_snippet(self, file_path):
        file = open(file_path, "wb")
        snippet_xml = template % (
            self.snippet_text,
            self.trigger,
            self.description,
            self.scopes
        )
        if int(sublime.version()) < 3000:
            file.write(bytes(snippet_xml))
        else:
            file.write(bytes(snippet_xml, 'UTF-8'))
        file.close()


class EditSnippetCommand(sublime_plugin.WindowCommand):
    def run(self):

        snippets = get_snippets()

        def on_done(index):
            if index >= 0:
                self.window.open_file(snippets[index][1])
            else:
                view = self.window.active_view()
                if self.window.get_view_index(view)[1] == -1:
                    view.close()

        def on_highlight(index):
            if index >= 0:
                self.window.open_file(snippets[index][1], sublime.TRANSIENT)

        self.window.show_quick_panel(
            [_[0] for _ in snippets],
            on_done,
            0,
            -1,
            on_highlight
        )

    def is_visible(self):
        return int(sublime.version()) > 3000


class DeleteSnippetCommand(sublime_plugin.WindowCommand):
    def run(self):

        snippets = get_snippets()

        def on_done(index):
            if index != -1:
                if int(sublime.version()) < 3000:
                    import send2trash
                else:
                    import Default.send2trash as send2trash
                snippet = get_snippets()[index]
                send2trash.send2trash(snippet[1])
                sublime.status_message(snippet[0] + " deleted")

            view = self.window.active_view()
            if self.window.get_view_index(view)[1] == -1:
                view.close()

        def on_highlight(index):
            if index >= 0:
                self.window.open_file(snippets[index][1], sublime.TRANSIENT)

        self.window.show_quick_panel(
            [_[0] for _ in snippets],
            on_done,
            0,
            -1,
            on_highlight
        )

    def is_visible(self):
        return int(sublime.version()) > 3000
