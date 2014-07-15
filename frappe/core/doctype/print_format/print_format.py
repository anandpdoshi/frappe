# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe, os
from frappe import _
import frappe.utils
from frappe.modules import get_doc_path
from jinja2 import TemplateNotFound

standard_format = "templates/print_formats/standard.html"

from frappe.model.document import Document

class PrintFormat(Document):
	def validate(self):
		if self.standard=="Yes" and frappe.session.user != "Administrator":
			frappe.throw(frappe._("Standard Print Format cannot be updated"))

		# old_doc_type is required for clearing item cache
		self.old_doc_type = frappe.db.get_value('Print Format',
				self.name, 'doc_type')

	def on_update(self):
		if hasattr(self, 'old_doc_type') and self.old_doc_type:
			frappe.clear_cache(doctype=self.old_doc_type)
		if self.doc_type:
			frappe.clear_cache(doctype=self.doc_type)

		self.export_doc()

	def export_doc(self):
		# export
		if self.standard == 'Yes' and (frappe.conf.get('developer_mode') or 0) == 1:
			from frappe.modules.export_file import export_to_files
			export_to_files(record_list=[['Print Format', self.name]],
				record_module=self.module)

	def on_trash(self):
		if self.doc_type:
			frappe.clear_cache(doctype=self.doc_type)

def get_args():
	if not frappe.form_dict.format:
		frappe.form_dict.format = standard_format
	if not frappe.form_dict.doctype or not frappe.form_dict.name:
		return {
			"body": """<h1>Error</h1>
				<p>Parameters doctype, name and format required</p>
				<pre>%s</pre>""" % repr(frappe.form_dict)
		}

	doc = frappe.get_doc(frappe.form_dict.doctype, frappe.form_dict.name)
	for ptype in ("read", "print"):
		if not frappe.has_permission(doc.doctype, ptype, doc):
			return {
				"body": """<h1>Error</h1>
					<p>No {ptype} permission</p>""".format(ptype=ptype)
			}

	return {
		"body": get_html(doc),
		"css": get_print_style(frappe.form_dict.style),
		"comment": frappe.session.user
	}

def get_html(doc, name=None, print_format=None):
	from jinja2 import Environment

	if isinstance(doc, basestring) and isinstance(name, basestring):
		doc = frappe.get_doc(doc, name)

	format_name = print_format or frappe.form_dict.format

	if format_name==standard_format:
		template = frappe.get_template("templates/print_formats/standard.html")
	else:
		template = Environment().from_string(get_print_format(doc.doctype,
			format_name))

	args = {
		"doc": doc,
		"meta": frappe.get_meta(doc.doctype),
		"frappe": frappe,
		"utils": frappe.utils,
		"is_visible": lambda tdf: tdf.fieldtype not in ("Column Break",
			"Section Break") and tdf.label and not tdf.print_hide and not tdf.hidden
	}
	html = template.render(args)
	return html

def get_print_format(doctype, format_name):
	if format_name==standard_format:
		return format_name

	opts = frappe.db.get_value("Print Format", format_name, "disabled", as_dict=True)
	if not opts:
		frappe.throw(_("Print Format {0} does not exist").format(format_name), frappe.DoesNotExistError)
	elif opts.disabled:
		frappe.throw(_("Print Format {0} is disabled").format(format_name), frappe.DoesNotExistError)

	# server, find template
	path = os.path.join(get_doc_path(frappe.db.get_value("DocType", doctype, "module"),
		"Print Format", format_name), frappe.scrub(format_name) + ".html")

	if os.path.exists(path):
		with open(path, "r") as pffile:
			return pffile.read()
	else:
		html = frappe.db.get_value("Print Format", format_name, "html")
		if html:
			return html
		else:
			frappe.throw(_("No template found at path: {0}").format(path),
				frappe.TemplateNotFoundError)

def get_print_style(style=None):
	if not style:
		style = frappe.db.get_default("print_style") or "Standard"

	try:
		return frappe.get_template("templates/styles/" + style.lower() + ".css").render()
	except TemplateNotFound:
		return frappe.get_template("templates/styles/standard.css").render()

