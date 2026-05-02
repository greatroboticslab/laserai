<Global.Microsoft.VisualBasic.CompilerServices.DesignerGenerated()> _
Partial Class Compensation
    Inherits System.Windows.Forms.Form

    'Form overrides dispose to clean up the component list.
    <System.Diagnostics.DebuggerNonUserCode()> _
    Protected Overrides Sub Dispose(ByVal disposing As Boolean)
        Try
            If disposing AndAlso components IsNot Nothing Then
                components.Dispose()
            End If
        Finally
            MyBase.Dispose(disposing)
        End Try
    End Sub

    'Required by the Windows Form Designer
    Private components As System.ComponentModel.IContainer

    'NOTE: The following procedure is required by the Windows Form Designer
    'It can be modified using the Windows Form Designer.  
    'Do not modify it using the code editor.
    <System.Diagnostics.DebuggerStepThrough()> _
    Private Sub InitializeComponent()
        Me.TableLayoutPanel1 = New System.Windows.Forms.TableLayoutPanel()
        Me.Humidity_Auto_Checkbox = New System.Windows.Forms.CheckBox()
        Me.Pressure_Auto_CheckBox = New System.Windows.Forms.CheckBox()
        Me.Temperature_Auto_CheckBox = New System.Windows.Forms.CheckBox()
        Me.ComboBox_TempUnits = New System.Windows.Forms.ComboBox()
        Me.TextBox_ECValue = New System.Windows.Forms.TextBox()
        Me.TextBox_Pressure = New System.Windows.Forms.TextBox()
        Me.NumericUpDown_Humidity = New System.Windows.Forms.NumericUpDown()
        Me.NumericUpDown_Pressure = New System.Windows.Forms.NumericUpDown()
        Me.TextBox_HumiFactor = New System.Windows.Forms.TextBox()
        Me.TextBox_PresFactor = New System.Windows.Forms.TextBox()
        Me.TextBox_ECParameter = New System.Windows.Forms.TextBox()
        Me.TextBox_ECFactor = New System.Windows.Forms.TextBox()
        Me.ComboBox_Pressure_Units = New System.Windows.Forms.ComboBox()
        Me.ComboBox_Humidity_Units = New System.Windows.Forms.ComboBox()
        Me.NumericUpDown_Temperature = New System.Windows.Forms.NumericUpDown()
        Me.TextBox_Temperature = New System.Windows.Forms.TextBox()
        Me.TextBox_Humidity = New System.Windows.Forms.TextBox()
        Me.Textbox_ECUnits = New System.Windows.Forms.TextBox()
        Me.TextBox1 = New System.Windows.Forms.TextBox()
        Me.TextBox_TempFactor = New System.Windows.Forms.TextBox()
        Me.WL_Label = New System.Windows.Forms.TextBox()
        Me.TextBox3 = New System.Windows.Forms.TextBox()
        Me.NumericUpDown_Wavelength = New System.Windows.Forms.NumericUpDown()
        Me.CMPDone_Button = New System.Windows.Forms.Button()
        Me.ECOff_Button = New System.Windows.Forms.Button()
        Me.ECOn_Button = New System.Windows.Forms.Button()
        Me.TableLayoutPanel1.SuspendLayout()
        CType(Me.NumericUpDown_Humidity, System.ComponentModel.ISupportInitialize).BeginInit()
        CType(Me.NumericUpDown_Pressure, System.ComponentModel.ISupportInitialize).BeginInit()
        CType(Me.NumericUpDown_Temperature, System.ComponentModel.ISupportInitialize).BeginInit()
        CType(Me.NumericUpDown_Wavelength, System.ComponentModel.ISupportInitialize).BeginInit()
        Me.SuspendLayout()
        '
        'TableLayoutPanel1
        '
        Me.TableLayoutPanel1.AccessibleName = ""
        Me.TableLayoutPanel1.CellBorderStyle = System.Windows.Forms.TableLayoutPanelCellBorderStyle.[Single]
        Me.TableLayoutPanel1.ColumnCount = 5
        Me.TableLayoutPanel1.ColumnStyles.Add(New System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 51.26904!))
        Me.TableLayoutPanel1.ColumnStyles.Add(New System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Percent, 48.73096!))
        Me.TableLayoutPanel1.ColumnStyles.Add(New System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Absolute, 143.0!))
        Me.TableLayoutPanel1.ColumnStyles.Add(New System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Absolute, 124.0!))
        Me.TableLayoutPanel1.ColumnStyles.Add(New System.Windows.Forms.ColumnStyle(System.Windows.Forms.SizeType.Absolute, 77.0!))
        Me.TableLayoutPanel1.Controls.Add(Me.Humidity_Auto_Checkbox, 4, 3)
        Me.TableLayoutPanel1.Controls.Add(Me.Pressure_Auto_CheckBox, 4, 2)
        Me.TableLayoutPanel1.Controls.Add(Me.Temperature_Auto_CheckBox, 4, 1)
        Me.TableLayoutPanel1.Controls.Add(Me.ComboBox_TempUnits, 2, 1)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_ECValue, 1, 0)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_Pressure, 0, 2)
        Me.TableLayoutPanel1.Controls.Add(Me.NumericUpDown_Humidity, 1, 3)
        Me.TableLayoutPanel1.Controls.Add(Me.NumericUpDown_Pressure, 1, 2)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_HumiFactor, 3, 3)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_PresFactor, 3, 2)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_ECParameter, 0, 0)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_ECFactor, 3, 0)
        Me.TableLayoutPanel1.Controls.Add(Me.ComboBox_Pressure_Units, 2, 2)
        Me.TableLayoutPanel1.Controls.Add(Me.ComboBox_Humidity_Units, 2, 3)
        Me.TableLayoutPanel1.Controls.Add(Me.NumericUpDown_Temperature, 1, 1)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_Temperature, 0, 1)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_Humidity, 0, 3)
        Me.TableLayoutPanel1.Controls.Add(Me.Textbox_ECUnits, 2, 0)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox1, 4, 0)
        Me.TableLayoutPanel1.Controls.Add(Me.TextBox_TempFactor, 3, 1)
        Me.TableLayoutPanel1.Location = New System.Drawing.Point(43, 36)
        Me.TableLayoutPanel1.Margin = New System.Windows.Forms.Padding(4)
        Me.TableLayoutPanel1.Name = "TableLayoutPanel1"
        Me.TableLayoutPanel1.RowCount = 4
        Me.TableLayoutPanel1.RowStyles.Add(New System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 43.93939!))
        Me.TableLayoutPanel1.RowStyles.Add(New System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Percent, 56.06061!))
        Me.TableLayoutPanel1.RowStyles.Add(New System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 36.0!))
        Me.TableLayoutPanel1.RowStyles.Add(New System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 37.0!))
        Me.TableLayoutPanel1.RowStyles.Add(New System.Windows.Forms.RowStyle(System.Windows.Forms.SizeType.Absolute, 25.0!))
        Me.TableLayoutPanel1.Size = New System.Drawing.Size(571, 150)
        Me.TableLayoutPanel1.TabIndex = 3
        '
        'Humidity_Auto_Checkbox
        '
        Me.Humidity_Auto_Checkbox.Anchor = CType((System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Bottom), System.Windows.Forms.AnchorStyles)
        Me.Humidity_Auto_Checkbox.AutoSize = True
        Me.Humidity_Auto_Checkbox.CheckAlign = System.Drawing.ContentAlignment.MiddleRight
        Me.Humidity_Auto_Checkbox.Font = New System.Drawing.Font("Microsoft Sans Serif", 8.5!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.Humidity_Auto_Checkbox.Location = New System.Drawing.Point(522, 115)
        Me.Humidity_Auto_Checkbox.Margin = New System.Windows.Forms.Padding(4)
        Me.Humidity_Auto_Checkbox.Name = "Humidity_Auto_Checkbox"
        Me.Humidity_Auto_Checkbox.Size = New System.Drawing.Size(18, 30)
        Me.Humidity_Auto_Checkbox.TabIndex = 114
        Me.Humidity_Auto_Checkbox.TextAlign = System.Drawing.ContentAlignment.MiddleCenter
        Me.Humidity_Auto_Checkbox.UseVisualStyleBackColor = True
        '
        'Pressure_Auto_CheckBox
        '
        Me.Pressure_Auto_CheckBox.Anchor = CType((System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Bottom), System.Windows.Forms.AnchorStyles)
        Me.Pressure_Auto_CheckBox.AutoSize = True
        Me.Pressure_Auto_CheckBox.CheckAlign = System.Drawing.ContentAlignment.MiddleRight
        Me.Pressure_Auto_CheckBox.Font = New System.Drawing.Font("Microsoft Sans Serif", 8.5!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.Pressure_Auto_CheckBox.Location = New System.Drawing.Point(522, 78)
        Me.Pressure_Auto_CheckBox.Margin = New System.Windows.Forms.Padding(4)
        Me.Pressure_Auto_CheckBox.Name = "Pressure_Auto_CheckBox"
        Me.Pressure_Auto_CheckBox.Size = New System.Drawing.Size(18, 28)
        Me.Pressure_Auto_CheckBox.TabIndex = 113
        Me.Pressure_Auto_CheckBox.TextAlign = System.Drawing.ContentAlignment.MiddleCenter
        Me.Pressure_Auto_CheckBox.UseVisualStyleBackColor = True
        '
        'Temperature_Auto_CheckBox
        '
        Me.Temperature_Auto_CheckBox.Anchor = CType((System.Windows.Forms.AnchorStyles.Top Or System.Windows.Forms.AnchorStyles.Bottom), System.Windows.Forms.AnchorStyles)
        Me.Temperature_Auto_CheckBox.CheckAlign = System.Drawing.ContentAlignment.MiddleRight
        Me.Temperature_Auto_CheckBox.Font = New System.Drawing.Font("Microsoft Sans Serif", 8.5!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.Temperature_Auto_CheckBox.Location = New System.Drawing.Point(521, 37)
        Me.Temperature_Auto_CheckBox.Margin = New System.Windows.Forms.Padding(4)
        Me.Temperature_Auto_CheckBox.Name = "Temperature_Auto_CheckBox"
        Me.Temperature_Auto_CheckBox.Size = New System.Drawing.Size(20, 32)
        Me.Temperature_Auto_CheckBox.TabIndex = 110
        Me.Temperature_Auto_CheckBox.Text = " "
        Me.Temperature_Auto_CheckBox.TextAlign = System.Drawing.ContentAlignment.MiddleCenter
        Me.Temperature_Auto_CheckBox.UseVisualStyleBackColor = True
        '
        'ComboBox_TempUnits
        '
        Me.ComboBox_TempUnits.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.ComboBox_TempUnits.FormattingEnabled = True
        Me.ComboBox_TempUnits.Items.AddRange(New Object() {"Degrees C", "Degrees F", "Degrees K"})
        Me.ComboBox_TempUnits.Location = New System.Drawing.Point(247, 41)
        Me.ComboBox_TempUnits.Margin = New System.Windows.Forms.Padding(4)
        Me.ComboBox_TempUnits.Name = "ComboBox_TempUnits"
        Me.ComboBox_TempUnits.RightToLeft = System.Windows.Forms.RightToLeft.No
        Me.ComboBox_TempUnits.Size = New System.Drawing.Size(95, 24)
        Me.ComboBox_TempUnits.TabIndex = 35
        Me.ComboBox_TempUnits.Text = "Degrees C"
        '
        'TextBox_ECValue
        '
        Me.TextBox_ECValue.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_ECValue.BackColor = System.Drawing.SystemColors.Control
        Me.TextBox_ECValue.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.TextBox_ECValue.Font = New System.Drawing.Font("Microsoft Sans Serif", 9.0!, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.TextBox_ECValue.Location = New System.Drawing.Point(141, 8)
        Me.TextBox_ECValue.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_ECValue.Name = "TextBox_ECValue"
        Me.TextBox_ECValue.ReadOnly = True
        Me.TextBox_ECValue.Size = New System.Drawing.Size(55, 17)
        Me.TextBox_ECValue.TabIndex = 14
        Me.TextBox_ECValue.Text = "Value"
        Me.TextBox_ECValue.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'TextBox_Pressure
        '
        Me.TextBox_Pressure.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_Pressure.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.TextBox_Pressure.Font = New System.Drawing.Font("Microsoft Sans Serif", 8.5!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.TextBox_Pressure.Location = New System.Drawing.Point(16, 83)
        Me.TextBox_Pressure.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_Pressure.Name = "TextBox_Pressure"
        Me.TextBox_Pressure.ReadOnly = True
        Me.TextBox_Pressure.Size = New System.Drawing.Size(83, 17)
        Me.TextBox_Pressure.TabIndex = 4
        Me.TextBox_Pressure.Text = "Pressure"
        Me.TextBox_Pressure.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'NumericUpDown_Humidity
        '
        Me.NumericUpDown_Humidity.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.NumericUpDown_Humidity.Location = New System.Drawing.Point(134, 119)
        Me.NumericUpDown_Humidity.Margin = New System.Windows.Forms.Padding(4)
        Me.NumericUpDown_Humidity.Name = "NumericUpDown_Humidity"
        Me.NumericUpDown_Humidity.Size = New System.Drawing.Size(68, 22)
        Me.NumericUpDown_Humidity.TabIndex = 5
        Me.NumericUpDown_Humidity.TextAlign = System.Windows.Forms.HorizontalAlignment.Right
        Me.NumericUpDown_Humidity.Value = New Decimal(New Integer() {50, 0, 0, 0})
        '
        'NumericUpDown_Pressure
        '
        Me.NumericUpDown_Pressure.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.NumericUpDown_Pressure.DecimalPlaces = 1
        Me.NumericUpDown_Pressure.Increment = New Decimal(New Integer() {1, 0, 0, 65536})
        Me.NumericUpDown_Pressure.Location = New System.Drawing.Point(134, 81)
        Me.NumericUpDown_Pressure.Margin = New System.Windows.Forms.Padding(4)
        Me.NumericUpDown_Pressure.Maximum = New Decimal(New Integer() {1520, 0, 0, 0})
        Me.NumericUpDown_Pressure.Minimum = New Decimal(New Integer() {380, 0, 0, 0})
        Me.NumericUpDown_Pressure.Name = "NumericUpDown_Pressure"
        Me.NumericUpDown_Pressure.Size = New System.Drawing.Size(68, 22)
        Me.NumericUpDown_Pressure.TabIndex = 6
        Me.NumericUpDown_Pressure.TextAlign = System.Windows.Forms.HorizontalAlignment.Right
        Me.NumericUpDown_Pressure.Value = New Decimal(New Integer() {760, 0, 0, 0})
        '
        'TextBox_HumiFactor
        '
        Me.TextBox_HumiFactor.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_HumiFactor.Location = New System.Drawing.Point(379, 119)
        Me.TextBox_HumiFactor.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_HumiFactor.Name = "TextBox_HumiFactor"
        Me.TextBox_HumiFactor.ReadOnly = True
        Me.TextBox_HumiFactor.Size = New System.Drawing.Size(99, 22)
        Me.TextBox_HumiFactor.TabIndex = 10
        Me.TextBox_HumiFactor.Text = "1.000000000"
        '
        'TextBox_PresFactor
        '
        Me.TextBox_PresFactor.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_PresFactor.Location = New System.Drawing.Point(379, 81)
        Me.TextBox_PresFactor.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_PresFactor.Name = "TextBox_PresFactor"
        Me.TextBox_PresFactor.ReadOnly = True
        Me.TextBox_PresFactor.Size = New System.Drawing.Size(99, 22)
        Me.TextBox_PresFactor.TabIndex = 9
        Me.TextBox_PresFactor.Text = "1.000000000"
        '
        'TextBox_ECParameter
        '
        Me.TextBox_ECParameter.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_ECParameter.BackColor = System.Drawing.SystemColors.Control
        Me.TextBox_ECParameter.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.TextBox_ECParameter.Font = New System.Drawing.Font("Microsoft Sans Serif", 9.0!, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.TextBox_ECParameter.Location = New System.Drawing.Point(7, 8)
        Me.TextBox_ECParameter.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_ECParameter.Name = "TextBox_ECParameter"
        Me.TextBox_ECParameter.ReadOnly = True
        Me.TextBox_ECParameter.Size = New System.Drawing.Size(100, 17)
        Me.TextBox_ECParameter.TabIndex = 13
        Me.TextBox_ECParameter.Text = "Parameter"
        Me.TextBox_ECParameter.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'TextBox_ECFactor
        '
        Me.TextBox_ECFactor.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_ECFactor.BackColor = System.Drawing.SystemColors.Control
        Me.TextBox_ECFactor.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.TextBox_ECFactor.Font = New System.Drawing.Font("Microsoft Sans Serif", 9.0!, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.TextBox_ECFactor.Location = New System.Drawing.Point(395, 8)
        Me.TextBox_ECFactor.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_ECFactor.Name = "TextBox_ECFactor"
        Me.TextBox_ECFactor.ReadOnly = True
        Me.TextBox_ECFactor.Size = New System.Drawing.Size(68, 17)
        Me.TextBox_ECFactor.TabIndex = 15
        Me.TextBox_ECFactor.Text = "Factor"
        Me.TextBox_ECFactor.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'ComboBox_Pressure_Units
        '
        Me.ComboBox_Pressure_Units.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.ComboBox_Pressure_Units.FormattingEnabled = True
        Me.ComboBox_Pressure_Units.Items.AddRange(New Object() {"mm/Hg", "mBar"})
        Me.ComboBox_Pressure_Units.Location = New System.Drawing.Point(248, 80)
        Me.ComboBox_Pressure_Units.Margin = New System.Windows.Forms.Padding(4)
        Me.ComboBox_Pressure_Units.Name = "ComboBox_Pressure_Units"
        Me.ComboBox_Pressure_Units.RightToLeft = System.Windows.Forms.RightToLeft.No
        Me.ComboBox_Pressure_Units.Size = New System.Drawing.Size(93, 24)
        Me.ComboBox_Pressure_Units.TabIndex = 36
        Me.ComboBox_Pressure_Units.Text = "mm/Hg"
        '
        'ComboBox_Humidity_Units
        '
        Me.ComboBox_Humidity_Units.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.ComboBox_Humidity_Units.FormattingEnabled = True
        Me.ComboBox_Humidity_Units.Items.AddRange(New Object() {"Rel %"})
        Me.ComboBox_Humidity_Units.Location = New System.Drawing.Point(248, 118)
        Me.ComboBox_Humidity_Units.Margin = New System.Windows.Forms.Padding(4)
        Me.ComboBox_Humidity_Units.Name = "ComboBox_Humidity_Units"
        Me.ComboBox_Humidity_Units.RightToLeft = System.Windows.Forms.RightToLeft.No
        Me.ComboBox_Humidity_Units.Size = New System.Drawing.Size(93, 24)
        Me.ComboBox_Humidity_Units.TabIndex = 37
        Me.ComboBox_Humidity_Units.Text = "Rel %"
        '
        'NumericUpDown_Temperature
        '
        Me.NumericUpDown_Temperature.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.NumericUpDown_Temperature.DecimalPlaces = 1
        Me.NumericUpDown_Temperature.Increment = New Decimal(New Integer() {1, 0, 0, 65536})
        Me.NumericUpDown_Temperature.Location = New System.Drawing.Point(132, 42)
        Me.NumericUpDown_Temperature.Margin = New System.Windows.Forms.Padding(4)
        Me.NumericUpDown_Temperature.Maximum = New Decimal(New Integer() {70, 0, 0, 0})
        Me.NumericUpDown_Temperature.Name = "NumericUpDown_Temperature"
        Me.NumericUpDown_Temperature.Size = New System.Drawing.Size(73, 22)
        Me.NumericUpDown_Temperature.TabIndex = 2
        Me.NumericUpDown_Temperature.TextAlign = System.Windows.Forms.HorizontalAlignment.Right
        Me.NumericUpDown_Temperature.Value = New Decimal(New Integer() {20, 0, 0, 0})
        '
        'TextBox_Temperature
        '
        Me.TextBox_Temperature.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_Temperature.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.TextBox_Temperature.Font = New System.Drawing.Font("Microsoft Sans Serif", 8.5!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.TextBox_Temperature.Location = New System.Drawing.Point(16, 44)
        Me.TextBox_Temperature.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_Temperature.Name = "TextBox_Temperature"
        Me.TextBox_Temperature.ReadOnly = True
        Me.TextBox_Temperature.Size = New System.Drawing.Size(83, 17)
        Me.TextBox_Temperature.TabIndex = 1
        Me.TextBox_Temperature.Text = "Temperature"
        Me.TextBox_Temperature.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'TextBox_Humidity
        '
        Me.TextBox_Humidity.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_Humidity.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.TextBox_Humidity.Font = New System.Drawing.Font("Microsoft Sans Serif", 8.5!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.TextBox_Humidity.Location = New System.Drawing.Point(16, 121)
        Me.TextBox_Humidity.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_Humidity.Name = "TextBox_Humidity"
        Me.TextBox_Humidity.ReadOnly = True
        Me.TextBox_Humidity.Size = New System.Drawing.Size(83, 17)
        Me.TextBox_Humidity.TabIndex = 11
        Me.TextBox_Humidity.Text = "Humidity"
        Me.TextBox_Humidity.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'Textbox_ECUnits
        '
        Me.Textbox_ECUnits.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.Textbox_ECUnits.BackColor = System.Drawing.SystemColors.Control
        Me.Textbox_ECUnits.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.Textbox_ECUnits.Font = New System.Drawing.Font("Microsoft Sans Serif", 9.0!, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.Textbox_ECUnits.Location = New System.Drawing.Point(243, 8)
        Me.Textbox_ECUnits.Margin = New System.Windows.Forms.Padding(4)
        Me.Textbox_ECUnits.Name = "Textbox_ECUnits"
        Me.Textbox_ECUnits.Size = New System.Drawing.Size(103, 17)
        Me.Textbox_ECUnits.TabIndex = 16
        Me.Textbox_ECUnits.Text = "Units Select"
        Me.Textbox_ECUnits.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'TextBox1
        '
        Me.TextBox1.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox1.BackColor = System.Drawing.SystemColors.Control
        Me.TextBox1.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.TextBox1.Font = New System.Drawing.Font("Microsoft Sans Serif", 9.0!, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.TextBox1.Location = New System.Drawing.Point(504, 8)
        Me.TextBox1.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox1.Name = "TextBox1"
        Me.TextBox1.ReadOnly = True
        Me.TextBox1.Size = New System.Drawing.Size(53, 17)
        Me.TextBox1.TabIndex = 112
        Me.TextBox1.Text = "Auto"
        Me.TextBox1.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'TextBox_TempFactor
        '
        Me.TextBox_TempFactor.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox_TempFactor.Location = New System.Drawing.Point(379, 42)
        Me.TextBox_TempFactor.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox_TempFactor.Name = "TextBox_TempFactor"
        Me.TextBox_TempFactor.ReadOnly = True
        Me.TextBox_TempFactor.Size = New System.Drawing.Size(99, 22)
        Me.TextBox_TempFactor.TabIndex = 3
        Me.TextBox_TempFactor.Text = "1.000000000"
        '
        'WL_Label
        '
        Me.WL_Label.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.WL_Label.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.WL_Label.Font = New System.Drawing.Font("Microsoft Sans Serif", 8.5!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.WL_Label.Location = New System.Drawing.Point(427, 218)
        Me.WL_Label.Margin = New System.Windows.Forms.Padding(4)
        Me.WL_Label.Name = "WL_Label"
        Me.WL_Label.ReadOnly = True
        Me.WL_Label.Size = New System.Drawing.Size(139, 17)
        Me.WL_Label.TabIndex = 40
        Me.WL_Label.Text = "Vacuum Wavelength"
        Me.WL_Label.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'TextBox3
        '
        Me.TextBox3.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.TextBox3.BorderStyle = System.Windows.Forms.BorderStyle.None
        Me.TextBox3.Font = New System.Drawing.Font("Microsoft Sans Serif", 8.5!, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, CType(0, Byte))
        Me.TextBox3.Location = New System.Drawing.Point(111, 214)
        Me.TextBox3.Margin = New System.Windows.Forms.Padding(4)
        Me.TextBox3.Name = "TextBox3"
        Me.TextBox3.ReadOnly = True
        Me.TextBox3.Size = New System.Drawing.Size(185, 17)
        Me.TextBox3.TabIndex = 41
        Me.TextBox3.Text = "Wavelength Correction"
        Me.TextBox3.TextAlign = System.Windows.Forms.HorizontalAlignment.Center
        '
        'NumericUpDown_Wavelength
        '
        Me.NumericUpDown_Wavelength.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.NumericUpDown_Wavelength.DecimalPlaces = 6
        Me.NumericUpDown_Wavelength.Increment = New Decimal(New Integer() {1, 0, 0, 196608})
        Me.NumericUpDown_Wavelength.Location = New System.Drawing.Point(443, 249)
        Me.NumericUpDown_Wavelength.Margin = New System.Windows.Forms.Padding(4)
        Me.NumericUpDown_Wavelength.Maximum = New Decimal(New Integer() {1410065408, 2, 0, 196608})
        Me.NumericUpDown_Wavelength.Minimum = New Decimal(New Integer() {1, 0, 0, 196608})
        Me.NumericUpDown_Wavelength.Name = "NumericUpDown_Wavelength"
        Me.NumericUpDown_Wavelength.Size = New System.Drawing.Size(107, 22)
        Me.NumericUpDown_Wavelength.TabIndex = 42
        Me.NumericUpDown_Wavelength.TextAlign = System.Windows.Forms.HorizontalAlignment.Right
        Me.NumericUpDown_Wavelength.Value = New Decimal(New Integer() {632991372, 0, 0, 393216})
        '
        'CMPDone_Button
        '
        Me.CMPDone_Button.Anchor = System.Windows.Forms.AnchorStyles.None
        Me.CMPDone_Button.BackgroundImage = Global.uMDGUI.My.Resources.Resources.InActiveButton4
        Me.CMPDone_Button.BackgroundImageLayout = System.Windows.Forms.ImageLayout.Stretch
        Me.CMPDone_Button.FlatStyle = System.Windows.Forms.FlatStyle.Popup
        Me.CMPDone_Button.ForeColor = System.Drawing.Color.Black
        Me.CMPDone_Button.Location = New System.Drawing.Point(287, 313)
        Me.CMPDone_Button.Margin = New System.Windows.Forms.Padding(4)
        Me.CMPDone_Button.Name = "CMPDone_Button"
        Me.CMPDone_Button.Size = New System.Drawing.Size(89, 28)
        Me.CMPDone_Button.TabIndex = 1
        Me.CMPDone_Button.Text = "CLOSE"
        '
        'ECOff_Button
        '
        Me.ECOff_Button.BackColor = System.Drawing.SystemColors.Control
        Me.ECOff_Button.BackgroundImage = Global.uMDGUI.My.Resources.Resources.ActiveButton6
        Me.ECOff_Button.BackgroundImageLayout = System.Windows.Forms.ImageLayout.Stretch
        Me.ECOff_Button.FlatStyle = System.Windows.Forms.FlatStyle.Popup
        Me.ECOff_Button.ForeColor = System.Drawing.SystemColors.ActiveCaptionText
        Me.ECOff_Button.Location = New System.Drawing.Point(119, 247)
        Me.ECOff_Button.Margin = New System.Windows.Forms.Padding(4)
        Me.ECOff_Button.Name = "ECOff_Button"
        Me.ECOff_Button.Size = New System.Drawing.Size(63, 30)
        Me.ECOff_Button.TabIndex = 38
        Me.ECOff_Button.Text = "OFF"
        Me.ECOff_Button.UseVisualStyleBackColor = False
        '
        'ECOn_Button
        '
        Me.ECOn_Button.BackgroundImage = Global.uMDGUI.My.Resources.Resources.InActiveButton4
        Me.ECOn_Button.BackgroundImageLayout = System.Windows.Forms.ImageLayout.Stretch
        Me.ECOn_Button.FlatStyle = System.Windows.Forms.FlatStyle.Popup
        Me.ECOn_Button.ForeColor = System.Drawing.Color.Black
        Me.ECOn_Button.Location = New System.Drawing.Point(215, 247)
        Me.ECOn_Button.Margin = New System.Windows.Forms.Padding(4)
        Me.ECOn_Button.Name = "ECOn_Button"
        Me.ECOn_Button.Size = New System.Drawing.Size(73, 30)
        Me.ECOn_Button.TabIndex = 37
        Me.ECOn_Button.Text = "ON"
        Me.ECOn_Button.UseVisualStyleBackColor = True
        '
        'Compensation
        '
        Me.AcceptButton = Me.CMPDone_Button
        Me.AutoScaleDimensions = New System.Drawing.SizeF(8.0!, 16.0!)
        Me.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font
        Me.ClientSize = New System.Drawing.Size(655, 372)
        Me.Controls.Add(Me.NumericUpDown_Wavelength)
        Me.Controls.Add(Me.TextBox3)
        Me.Controls.Add(Me.WL_Label)
        Me.Controls.Add(Me.ECOff_Button)
        Me.Controls.Add(Me.ECOn_Button)
        Me.Controls.Add(Me.TableLayoutPanel1)
        Me.Controls.Add(Me.CMPDone_Button)
        Me.Margin = New System.Windows.Forms.Padding(4)
        Me.MaximizeBox = False
        Me.Name = "Compensation"
        Me.ShowIcon = False
        Me.StartPosition = System.Windows.Forms.FormStartPosition.CenterParent
        Me.Text = "Micro Measurement Display Environmental Compensation "
        Me.TableLayoutPanel1.ResumeLayout(False)
        Me.TableLayoutPanel1.PerformLayout()
        CType(Me.NumericUpDown_Humidity, System.ComponentModel.ISupportInitialize).EndInit()
        CType(Me.NumericUpDown_Pressure, System.ComponentModel.ISupportInitialize).EndInit()
        CType(Me.NumericUpDown_Temperature, System.ComponentModel.ISupportInitialize).EndInit()
        CType(Me.NumericUpDown_Wavelength, System.ComponentModel.ISupportInitialize).EndInit()
        Me.ResumeLayout(False)
        Me.PerformLayout()

    End Sub
    Friend WithEvents CMPDone_Button As System.Windows.Forms.Button
    Friend WithEvents TableLayoutPanel1 As System.Windows.Forms.TableLayoutPanel
    Friend WithEvents TextBox_Humidity As System.Windows.Forms.TextBox
    Friend WithEvents TextBox_TempFactor As System.Windows.Forms.TextBox
    Friend WithEvents NumericUpDown_Temperature As System.Windows.Forms.NumericUpDown
    Friend WithEvents TextBox_Pressure As System.Windows.Forms.TextBox
    Friend WithEvents NumericUpDown_Pressure As System.Windows.Forms.NumericUpDown
    Friend WithEvents NumericUpDown_Humidity As System.Windows.Forms.NumericUpDown
    Friend WithEvents TextBox_PresFactor As System.Windows.Forms.TextBox
    Friend WithEvents TextBox_HumiFactor As System.Windows.Forms.TextBox
    Friend WithEvents TextBox_Temperature As System.Windows.Forms.TextBox
    Friend WithEvents TextBox_ECValue As System.Windows.Forms.TextBox
    Friend WithEvents Textbox_ECUnits As System.Windows.Forms.TextBox
    Friend WithEvents TextBox_ECParameter As System.Windows.Forms.TextBox
    Friend WithEvents TextBox_ECFactor As System.Windows.Forms.TextBox
    Friend WithEvents ComboBox_TempUnits As System.Windows.Forms.ComboBox
    Friend WithEvents ComboBox_Pressure_Units As System.Windows.Forms.ComboBox
    Friend WithEvents ComboBox_Humidity_Units As System.Windows.Forms.ComboBox
    Friend WithEvents ECOff_Button As System.Windows.Forms.Button
    Friend WithEvents ECOn_Button As System.Windows.Forms.Button
    Friend WithEvents WL_Label As System.Windows.Forms.TextBox
    Friend WithEvents TextBox3 As System.Windows.Forms.TextBox
    Friend WithEvents NumericUpDown_Wavelength As System.Windows.Forms.NumericUpDown
    Friend WithEvents Humidity_Auto_Checkbox As System.Windows.Forms.CheckBox
    Friend WithEvents Pressure_Auto_CheckBox As System.Windows.Forms.CheckBox
    Friend WithEvents Temperature_Auto_CheckBox As System.Windows.Forms.CheckBox
    Friend WithEvents TextBox1 As System.Windows.Forms.TextBox
End Class
