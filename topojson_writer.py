# -*- coding: utf-8 -*-
"""
/***************************************************************************
 TopoJsonWriter
                                 A QGIS plugin
 Write vector layers to TopoJson
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-01-13
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Dror Bogin
        email                : Dror.Bogin@Gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, QgsMapLayer
from qgis import processing

#from PyQt5.QtWebEngineWidgets import QWebEngineView
from qgis.PyQt.QtWebKitWidgets import QWebView, QWebInspector, QWebPage
from qgis.PyQt.QtWebKit import QWebSettings

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .topojson_writer_dialog import TopoJsonWriterDialog
import os
import os.path
import tempfile
import json


class TopoJsonWriter:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.mb = self.iface.messageBar()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'TopoJsonWriter_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&TopoJSON Writer')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.dlg = TopoJsonWriterDialog()
        self.init_html()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('TopoJsonWriter', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/topojson_writer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Write layer to TopoJson'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&TopoJSON Writer'),
                action)
            self.iface.removeToolBarIcon(action)


    def load_vectors(self):
        """
        Populate the layer selection with vector layers only
        """
        self.dlg.layer_select.clear()
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        self.vector_layers = []
        self.layer_ids = []
        for layer in layers:
            if layer.type() ==  QgsMapLayer.VectorLayer:
                #if layer.geometryType() == 0:
                #    vector_layers.append(layer.name() + "("+layer.crs().authid() +")")
                #if layer.geometryType() == 1:
                #    vector_layers.append('≀' + layer.name())
                #if layer.geometryType() == 2:
                #    vector_layers.append('▙' + layer.name())
                self.vector_layers.append(layer.name() + " ("+layer.crs().authid() +") ")
                self.layer_ids.append(layer.id())
        self.dlg.layer_select.addItems(self.vector_layers)


    def init_html(self):
        self.dlg.view = QWebView()
        self.dlg.view.settings().setAttribute(
                QWebSettings.DeveloperExtrasEnabled, True)
        topo_js_path = os.path.abspath(os.path.join(self.plugin_dir, "base.html"))
        local_url = QUrl.fromLocalFile(topo_js_path)
        self.dlg.view.load(local_url)
        self.dlg.iframe_holder.addWidget(self.dlg.view)


    def complete_name(self):
        frame = self.dlg.view.page().mainFrame()
        print(frame.evaluateJavaScript('completeAndReturnName()'))#, self.store_value)


    def convert(self):
        frame = self.dlg.view.page().mainFrame()
        layerI = self.dlg.layer_select.currentIndex()
        layer = self.layer_ids[layerI]
        temp_name = next(tempfile._get_candidate_names())
        filename = os.path.join(self.plugin_dir, "{}.geojson".format(temp_name))
        processing.run("native:reprojectlayer",{'INPUT':layer,
                    'TARGET_CRS':'EPSG:4326',
                    'OUTPUT':filename})
        with open(filename, encoding='utf-8') as f:
                d = json.dumps(json.load(f))
                topojson_data = frame.evaluateJavaScript('convert({})'.format(d))
                self.save_topojson(topojson_data)
        os.remove(filename)
        

        



    def save_topojson(self,data):
        try:
            if isinstance(data, str):
                data = json.loads(data)
                
            if(len(self.dlg.save_file_name.filePath())) > 0:
                savePath = self.dlg.save_file_name.filePath()
                with open(savePath, 'w') as dst:
                    json.dump(data, dst, ensure_ascii=False, indent=4)

            else:
                self.mb.pushWarning('Can\'t save without a file path...','missing Path')
        except Exception as e:
            self.mb.pushCritical('Error',"Something went wrong with saving the TopoJson, please send us the following error: {}".format(e))  


    def store_value(self, param):
        value = param



    def run(self):
        """Run method that performs all the real work"""
            
        # show the dialog
        self.dlg.show()
        # Populate vector layers to combo box
        self.load_vectors()
        self.dlg.button.clicked.connect(self.convert)
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            self.complete_name()
