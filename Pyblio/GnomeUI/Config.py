# -*- coding: utf-8 -*-
# This file is part of pybliographer
# 
# Copyright (C) 1998-2004 Frederic GOBRY <gobry@pybliographer.org>
# Copyright (C) 2013 Germán Poo-Caamaño <gpoo@gnome.org>
# 	   
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2 
# of the License, or (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details. 
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
# 
# 

# TO DO:
# List view troubles

from gi.repository import GObject, Gtk

import copy, os.path, re, string   

from Pyblio.GnomeUI import Utils
from Pyblio import Config, version
from Pyblio.Utils import format

_map = string.maketrans ('\t\n', '  ')
_cpt = re.compile ('\s+')

class ConfigDialog (Utils.GladeWindow):

    gladeinfo = {
        'file': 'config1.ui',
        'root': 'config1',
        'name': 'configuration'
        }

    def __init__ (self, parent = None):

        Utils.GladeWindow.__init__ (self, parent)

        self.dialog = self.xml.get_object('config1')
        content = self.xml.get_object('dialog-vbox1')

        self.w = Gtk.Notebook ()

        content.pack_start (self.w, True, True, 0)
        
        self.warning = 0
        self.parent = parent
        
        domains = Config.domains ()
        domains = map (lambda x: string.capitalize (x), domains)
        domains.sort ()

        self.page = []
        
        for dom in domains:
            
            cw    = {}
            keys  = Config.keys_in_domain (string.lower (dom))
            keys.sort ()

            table = Gtk.VBox (spacing=6)
            table.set_border_width (12)
            
            for item in keys:
                data  = Config.get (item)
                if data.type is None or not hasattr (data.type, 'w'):
                    continue

                nice  = string.capitalize (string.split (item, '/') [1])
                label = Gtk.Label()
                label.set_use_markup(True)

                label.set_markup('<b>%s</b>' % (nice))
                label.set_alignment(xalign=0.5, yalign=0)
                hbox = Gtk.HBox (spacing = 12)
                hbox.pack_start(label, False, True, 0)
                
                desc  = data.description
                desc  = string.translate (desc, _map)
                desc  = string.strip (_cpt.sub (' ', desc))

                table.pack_start (hbox, False, True, 0)
                # Create the edition widget...
                edit = data.type.w (data.type, self, item, help_text=desc)
                if edit.allow_help:
                    label = Gtk.Label ()
                    label.set_line_wrap (True)
                    label.set_text(desc)
                    hbox.pack_start(label, False, True, 0)
                hbox = Gtk.HBox (spacing = 6)
                hbox.set_border_width (6)
                
                cw [item] = edit
                hbox.pack_start (edit.w, False, True, 0)

                table.pack_start (hbox,
                                  expand=edit.resize,
                                  fill  =edit.resize, padding=0)
                # items should not be spread vertically, however 
            if cw:
                # Put the complete table in a scrolled window
                scroll = Gtk.ScrolledWindow ()
                scroll.set_policy (Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
                
                scroll.add_with_viewport (table)
                
                self.w.append_page (scroll, Gtk.Label(label=dom))
                self.page.append (cw)

        self.show()
        return

    def on_close1 (self, w):

        self.size_save ()
        self.dialog.hide()

    def show (self):
        self.dialog.show_all()
        
    def changed (self):
        if not self.warning:
            self.warning = 1
            self.parent.warning (
                _("Some changes require to restart Pybliographic\n"
                  "to be correctly taken into account"))


class BaseConfig:
    def __init__ (self, dtype, props, key, parent=None, help_text=''):
        """Base class for configuration data display elements.
        dtype is the tpye attribute of the configuration data element
        props is the Dialog object
        key   is the name of the configuratio item
        help_txt its description
        """
        
        self.type    = dtype
        self.key     = key
        self.prop    = props
        self.parent  = parent
        self._state  = 0
        self.frozen  = 0
        self.allow_help = 1
        return

    def state (self):
        return self._state
    
    def changed (self, * arg):
        #print 'CHANGED:', self.key
        if self.frozen: return
        self._state = 1
        return

    def freeze (self):
        self.frozen = 1
        return

    def thaw (self):
        self.frozen = 0
        return

    def update (self, force=False, *args):
        """Call this with an additional parameter
        force=True if the widget does nor use changed()."""
        #print 'UPDATE:', self.key, self.get(), force
        if not (force or self.state ()): return 0
        if self.key:
            Config.set_and_save (self.key, self.get ())
            self.prop.changed()
        else:
            self.parent.update(force = force)
        return False


class StringConfig (BaseConfig):

    resize = False
    
    def __init__ (self, dtype, props, key=None, parent=None,  help_text=''):
        BaseConfig.__init__ (self, dtype, props, key, parent)
        
        self.w = Gtk.Entry ()
        
        if self.key:
            text = Config.get (key).data
            if text: self.w.set_text (text)

        self.w.connect ('focus-out-event', self.update)
        self.w.connect ('changed', self.changed)
        self.w.show_all ()
        return
        
    def get (self):
        return self.w.get_text ()

    def set (self, value):
        self.freeze ()
        self.w.set_text (value)
        self.thaw ()
        return
    

class IntegerConfig (StringConfig):

    resize = False
    
    def __init__ (self, dtype, props, key=None, parent=None,  help_text=''):
        BaseConfig.__init__ (self, dtype, props, key, parent)

        if self.key:
            value = Config.get (key).type
            
            vmin = value.min or 0
            vmax = value.max or +100
        else:
            vmin = 0
            vmax = +100
            
        adj = Gtk.Adjustment (0, vmin, vmax, 1, 10, 0)
        self.w = Gtk.SpinButton()
        self.w.configure(adj, 1, 0)
        
        if self.key:
            value = Config.get (key).data
            if value is not None: self.w.set_value (value)
        
        self.w.connect ('changed', self.update, True)
        self.w.connect ('focus-out-event', self.update)
        self.w.show_all ()
        return


    def get (self):
        value = self.w.get_value_as_int ()
        type = Config.get (self.key).type
        if type.min and value < type.min: return None
        if type.max and value > type.max: return None
        return value

    def set (self, value):
        self.freeze ()
        self.w.set_value (value)
        self.thaw ()
        return
    

class BooleanConfig (BaseConfig):

    resize = False

    def __init__ (self, dtype, props, key=None, parent=None,  help_text=''):
        BaseConfig.__init__ (self, dtype, props, key, parent)
        self.allow_help = False
        self.w = Gtk.HBox (spacing=6)
        self.button = Gtk.CheckButton ()
        self.w.pack_start (self.button, False, True, 0)

        if self.key:
            value = Config.get (key).data
            self.button.set_active(value)
        
        self.button.connect  ('clicked', self.update, True)
        description = Gtk.Label()
        description.set_use_markup(True)
        description.set_line_wrap(True)
        description.set_justify(Gtk.Justification.LEFT) #default?
        description.set_markup('%s' % (help_text))
        description.set_alignment(xalign=0.5, yalign=0.5)
        self.w.pack_start (description, False, True, 0)
        
        self.w.show_all ()
        return

    def get (self):
        # Python 2.2 considers True as an Int, and 2.3 as a
        # Boolean... So we cast it to an int for compatibility
        return self.button.get_active () + 0

    def set (self, value):
        self.freeze ()
        self.button.set_active(value)
        self.thaw ()
        return
    

class ElementConfig (BaseConfig):
    
    resize = False
    
    def __init__ (self, dtype, props, key=None, parent=None,  help_text=''):
        BaseConfig.__init__ (self, dtype, props, key, parent)

        if key:
            data = str(Config.get (key).data)
        else: data = ''

        self.m = Gtk.ComboBoxText ()
        self.items = dtype.get ()

        ix = 0
        select = -1
        for i in self.items:
            self.m.append_text (str (i))
            if data == str(i):
                select = ix
            ix += 1
        
        self.m.set_active (select)
        self.m.connect ('changed', self.update, True)
        
        self.w = Gtk.HBox(spacing = 12)
        self.w.pack_start(self.m, True, True, padding=12)
        self.w.show_all ()
        return

    def get (self):
        return self.items[self.m.get_active ()]
    
    def set (self, value):
        self.freeze ()
        self.m.set_active (self.items.index (value))
        self.thaw ()
        return
    
class TupleConfig (BaseConfig):

    def __init__ (self, dtype, props, key=None, parent=None,  help_text=''):
        BaseConfig.__init__ (self, dtype, props, key, parent)
        self.w = Gtk.VBox (spacing = 6)
        self.sub = []

        self.resize = False

        for sub in dtype.subtypes:
            w = sub.w (sub, props, parent=self)
            self.sub.append (w)
            
            if w.resize:
                self.resize = True

        for w in self.sub:
            self.w.pack_start (w.w, expand=w.resize, fill=w.resize, padding=0)
        
        if key:
            data = Config.get (key).data
            i = 0
            for item in data:
                self.sub [i].set (item)
                i = i + 1
        self.w.show_all ()
        return

    def state (self):
        for item in self.sub:
            if item.state (): return 1
        return 0
    
    def get (self):
        ret = []
        for item in self.sub:
            ret.append (item.get ())
        return ret

    def set (self, value):
        self.freeze ()
        i = 0
        for item in value:
            #print 'SET TUPLE:', value, item
            self.sub [i].set (item)
            i = i + 1
        self.thaw ()
        self.update(True)
        return


class ListConfig (BaseConfig):

    resize = True
    
    def __init__ (self, dtype, props, key=None, parent=None,  help_text=''):
        BaseConfig.__init__ (self, dtype, props, key, parent)
        self.w = Gtk.VBox (spacing = 6)
        h = Gtk.HBox (spacing = 6)
        scroll = Gtk.ScrolledWindow ()
        scroll.set_policy (Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.m = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT)
        self.v = Gtk.TreeView(self.m)
        self.v.set_reorderable (True)
        self.v.set_headers_visible (False)
        rend = Gtk.CellRendererText ()
        col = Gtk.TreeViewColumn ('', rend, text=0)
        col.set_resizable(True)
        #col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        col.set_min_width(200)
        self.v.append_column (col)
        self.s = self.v.get_selection()
        self.s.connect ('changed', self.select_cb)
        
        scroll.add (self.v)
        h.pack_start (scroll, True, True, 0)
        bbox = Gtk.VButtonBox ()

        button = Gtk.Button (_("Add"))
        bbox.pack_start (button, True, True, 0)
        button.connect ('clicked', self.add_cb)
        button = Gtk.Button (_("Update"))
        bbox.pack_start (button, True, True, 0)
        button.connect ('clicked', self.update_cb)
        button = Gtk.Button (_("Remove"))
        bbox.pack_start (button, True, True, 0)
        button.connect ('clicked', self.remove_cb)

        self.m.connect ('row-changed', self._on_reordering)
        self.w.connect ('hide', self._on_leave)
        
        h.pack_end (bbox, False, True, 0)
        self.w.pack_start (h, True, True, 0)

        # Bottom
        self.subw = dtype.subtype.w (dtype.subtype, props, parent=self)
        self.w.pack_start (self.subw.w, expand=self.subw.resize,
                           fill=self.subw.resize, padding=0)
        if self.key:
            data = Config.get (self.key).data
            self.set (data)
           
        self.w.show_all ()
        return

    def add_cb (self, * arg):
        data = self.subw.get ()
        if not data: return
        
        self.m.append ((str (data), data))
        self.update (True)
        return

    def remove_cb (self, * arg):
        if not self.s: return
        m, iter = self.s.get_selected()
        m.remove(iter)
        self.update (True)
        return

    def update_cb (self, * arg):
        if not self.s: return
        data = self.subw.get ()
        m, row  = self.s.get_selected()
        m[row] = (str(data), data)
        return

    def select_cb (self, *args):
        m, row = self.s.get_selected()
        if row:
            data = m.get_value(row, 1)
            self.subw.set (data)
        return

    def set (self, data):
        self.freeze ()
        for item in data:
            self.m.append((str(item), item))
        self.thaw ()
        return

    def get (self):
        ret = []
        for i in self.m:
            data = i[1]
            ret.append (data)
        return ret

    def _on_reordering (self, m, p, i):
        if self.frozen: return

        self.changed ()
        return

    def _on_leave (self, * args):
        self.update ()
        return
        
    
class DictConfig (BaseConfig):

    resize = True
    
    def __init__ (self, dtype, props, key=None, parent=None, help_text=''):
        BaseConfig.__init__ (self, dtype, props, key, parent)
        self.w = Gtk.VBox (spacing = 6)
        h = Gtk.HBox (spacing = 6)
        scroll = Gtk.ScrolledWindow ()
        scroll.set_policy (Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.m = Gtk.ListStore(GObject.TYPE_STRING,
                               GObject.TYPE_STRING,
                               GObject.TYPE_PYOBJECT)
        self.v = Gtk.TreeView(self.m)

        rend = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn('Key', rend, text=0)
        col.set_resizable(True)
        #col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        col.set_min_width(100)
        self.v.append_column(col)
       
        rend = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn('Value', rend, text=1)
        self.v.append_column(col)

        self.s = self.v.get_selection()
        self.s.connect ('changed', self.select_cb)
        
        scroll.add (self.v)
        h.pack_start (scroll, True, True, 0)

        bbox = Gtk.VButtonBox ()

        button = Gtk.Button (_("Set"))
        bbox.pack_start (button, True, True, 0)
        button.connect ('clicked', self.update_cb)
        button = Gtk.Button (_("Remove"))
        bbox.pack_start (button, True, True, 0)
        button.connect ('clicked', self.remove_cb)

        h.pack_start (bbox, False, False, 0)
        self.w.pack_start (h, True, True, 0)
        self.w.pack_start(Gtk.HSeparator(), expand=False, fill=False,
                          padding=0)
        
        # Bottom
        table = Gtk.Table (2, 2, homogeneous = False)
        table.set_row_spacings (6)
        table.set_col_spacings (6)
        table.attach (Gtk.Label(label=_("Key:")), 0, 1, 0, 1,
                      xoptions = 0, yoptions = 0)
        table.attach (Gtk.Label(label=_("Value:")), 0, 1, 1, 2,
                      xoptions = 0, yoptions = 0)

        self.keyw   = dtype.key.w (dtype.key, props, parent=self)
        if self.keyw.resize:
            table.attach (self.keyw.w, 1, 2, 0, 1)
        else:
            table.attach (self.keyw.w, 1, 2, 0, 1,
                          yoptions = 0)
            
        self.valuew = dtype.value.w (dtype.value, props, parent=self)
        if self.valuew.resize:
            table.attach (self.valuew.w, 1, 2, 1, 2)
        else:
            table.attach (self.valuew.w, 1, 2, 1, 2,
                          yoptions = 0)
            
        self.w.pack_start (table, True, True, 0)
        self.dict = {}
        
        if self.key:
            data = Config.get (self.key).data
            self.dict = copy.copy (data)
            keys = data.keys ()
            keys.sort ()
            for k in keys:
                v = data [k]
                self.m.append ((str (k), str (v), v))
        self.w.show_all ()
        return

    def remove_cb (self, * arg):
        
        if not self.s: return
        self.changed ()
        m, iter = self.s.get_selected()
        #print 'REMOVE:', m, iter, dict
        key = m.get_value(iter, 0)
        path = m.get_path(iter)
        m.remove(iter)
        m.row_deleted(path)
        del self.dict [key]
        return

    def update_cb (self, * arg):
        self.changed ()
        m, row = self.s.get_selected()
        key = self.keyw.get()
        #print 'UPDATE:', self.valuew.get()
        try:
            val = tuple(self.valuew.get())
        except TypeError:
            val = self.valuew.get()
        if self.dict.has_key (key):
            for i in m:
                if i[0] == key:
                    m [i.iter] =  (key, str(val), val)
                    m.row_changed(i.path, i.iter)
                    break
            else:
                print 'ERROR'
        else:
            iter = m.append ((key, str(val), val))
            i = m[iter]
            #m.row_inserted (i.path, i.iter)
        self.dict [key] = val
        self.update()
        pass
    

    def select_cb (self, *args):
        m, row = self.s.get_selected()
        #print 'SELECT:', m, row
        if row:
            self.keyw.set   (m.get_value(row, 0))
            self.valuew.set (m.get_value(row, 2))
        return

    def set (self, data):
        self.freeze ()
        self.m.clear ()
        
        self.dict = copy.copy (data)
        keys = data.keys ()
        keys.sort ()
        for k in keys:
            v = data [k]
            self.m.append ((str (k), str (v)))
        self.thaw ()
        return

    def get (self):
        return self.dict
    
    
Config.Boolean.w = BooleanConfig
Config.String.w  = StringConfig
Config.Integer.w = IntegerConfig
Config.Element.w = ElementConfig
Config.Tuple.w   = TupleConfig
Config.List.w    = ListConfig
Config.Dict.w    = DictConfig

__dialog_object = None

def run (w):
    global __dialog_object

    if not __dialog_object:
        __dialog_object = ConfigDialog(w)

    __dialog_object.show()

    
# Local Variables:
# py-master-file: "tConfig.py"
# End:

