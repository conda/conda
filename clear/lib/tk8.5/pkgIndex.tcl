if {[catch {package present Tcl 8.5.0}]} return
package ifneeded Tk 8.5.18 [list load [file normalize [file join $dir .. libtk8.5.dylib]] Tk]
