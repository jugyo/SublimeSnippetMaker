import sublime, sublime_plugin
import os, re
from glob import iglob

template = """<snippet>
  <!-- Example: Hello, ${1:this} is a ${2:snippet}. -->
  <content><![CDATA[
%s
]]></content>
  <!-- Optional: Set a tabTrigger to define how to trigger the snippet -->
  <tabTrigger>%s</tabTrigger>
  <description>%s</description>
  <!-- Optional: Set a scope to limit where the snippet will trigger -->
  <scope>%s</scope>
</snippet>"""

class MakeSnippetCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.snippet_text = "\n".join([self.view.substr(i) for i in self.view.sel()])
        self.view.window().show_input_panel('Trigger', '', self.set_trigger, None, None)

    def set_trigger(self, trigger):
        self.trigger = trigger
        self.view.window().show_input_panel('Description', '', self.set_description, None, None)

    def set_description(self, description):
        self.description = description
        scopes = self.view.scope_name(self.view.sel()[0].begin()).strip().replace(' ', ', ')
        self.view.window().show_input_panel('Scope', scopes, self.set_scopes, None, None)

    def set_scopes(self, scopes):
        self.scopes = scopes
        self.ask_file_name()

    def ask_file_name(self):
        self.view.window().show_input_panel('File Name', self.trigger + '.sublime-snippet', self.make_snippet, None, None)

    def make_snippet(self, file_name):
        if re.match('^\w+\.sublime\-snippet$', file_name):
            file_path = os.path.join(sublime.packages_path(), 'User', file_name)

            if os.path.exists(file_path):
                if sublime.ok_cancel_dialog('Override %s?' % file_name) is False:
                    self.ask_file_name()
                    return

            file = open(file_path, "wb")
            snippet_xml = template % (self.snippet_text, self.trigger, self.description, self.scopes)
            if int(sublime.version()) >= 3000:
                file.write(bytes(snippet_xml, 'UTF-8'))
            else: # To support Sublime Text 2
                file.write(bytes(snippet_xml))
            file.close()

            self.view.window().open_file(file_path)
        else:
            sublime.error_message('Please specify a valid snippet file name!! i.e. `awesome.sublime-snippet`')
            self.ask_file_name()

class EditSnippetCommand(sublime_plugin.WindowCommand):
    def run(self):
        snippets = [
            [os.path.basename(filepath), filepath]
                for filepath
                    in iglob(os.path.join(sublime.packages_path(), 'User', '*.sublime-snippet'))]

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

        self.window.show_quick_panel([_[0] for _ in snippets], on_done, sublime.MONOSPACE_FONT, -1, on_highlight)
