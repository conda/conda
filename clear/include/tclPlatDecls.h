/*
 * tclPlatDecls.h --
 *
 *	Declarations of platform specific Tcl APIs.
 *
 * Copyright (c) 1998-1999 by Scriptics Corporation.
 * All rights reserved.
 */

#ifndef _TCLPLATDECLS
#define _TCLPLATDECLS

#undef TCL_STORAGE_CLASS
#ifdef BUILD_tcl
#   define TCL_STORAGE_CLASS DLLEXPORT
#else
#   ifdef USE_TCL_STUBS
#      define TCL_STORAGE_CLASS
#   else
#      define TCL_STORAGE_CLASS DLLIMPORT
#   endif
#endif

/*
 * TCHAR is needed here for win32, so if it is not defined yet do it here.
 * This way, we don't need to include <tchar.h> just for one define.
 */
#if (defined(_WIN32) || defined(__CYGWIN__)) && !defined(_TCHAR_DEFINED)
#   if defined(_UNICODE)
	typedef wchar_t TCHAR;
#   else
	typedef char TCHAR;
#   endif
#   define _TCHAR_DEFINED
#endif

/* !BEGIN!: Do not edit below this line. */

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Exported function declarations:
 */

#if defined(__WIN32__) || defined(__CYGWIN__) /* WIN */
#ifndef Tcl_WinUtfToTChar_TCL_DECLARED
#define Tcl_WinUtfToTChar_TCL_DECLARED
/* 0 */
EXTERN TCHAR *		Tcl_WinUtfToTChar(CONST char *str, int len,
				Tcl_DString *dsPtr);
#endif
#ifndef Tcl_WinTCharToUtf_TCL_DECLARED
#define Tcl_WinTCharToUtf_TCL_DECLARED
/* 1 */
EXTERN char *		Tcl_WinTCharToUtf(CONST TCHAR *str, int len,
				Tcl_DString *dsPtr);
#endif
#endif /* WIN */
#ifdef MAC_OSX_TCL /* MACOSX */
#ifndef Tcl_MacOSXOpenBundleResources_TCL_DECLARED
#define Tcl_MacOSXOpenBundleResources_TCL_DECLARED
/* 0 */
EXTERN int		Tcl_MacOSXOpenBundleResources(Tcl_Interp *interp,
				CONST char *bundleName, int hasResourceFile,
				int maxPathLen, char *libraryPath);
#endif
#ifndef Tcl_MacOSXOpenVersionedBundleResources_TCL_DECLARED
#define Tcl_MacOSXOpenVersionedBundleResources_TCL_DECLARED
/* 1 */
EXTERN int		Tcl_MacOSXOpenVersionedBundleResources(
				Tcl_Interp *interp, CONST char *bundleName,
				CONST char *bundleVersion,
				int hasResourceFile, int maxPathLen,
				char *libraryPath);
#endif
#endif /* MACOSX */

typedef struct TclPlatStubs {
    int magic;
    struct TclPlatStubHooks *hooks;

#if defined(__WIN32__) || defined(__CYGWIN__) /* WIN */
    TCHAR * (*tcl_WinUtfToTChar) (CONST char *str, int len, Tcl_DString *dsPtr); /* 0 */
    char * (*tcl_WinTCharToUtf) (CONST TCHAR *str, int len, Tcl_DString *dsPtr); /* 1 */
#endif /* WIN */
#ifdef MAC_OSX_TCL /* MACOSX */
    int (*tcl_MacOSXOpenBundleResources) (Tcl_Interp *interp, CONST char *bundleName, int hasResourceFile, int maxPathLen, char *libraryPath); /* 0 */
    int (*tcl_MacOSXOpenVersionedBundleResources) (Tcl_Interp *interp, CONST char *bundleName, CONST char *bundleVersion, int hasResourceFile, int maxPathLen, char *libraryPath); /* 1 */
#endif /* MACOSX */
} TclPlatStubs;

extern TclPlatStubs *tclPlatStubsPtr;

#ifdef __cplusplus
}
#endif

#if defined(USE_TCL_STUBS) && !defined(USE_TCL_STUB_PROCS)

/*
 * Inline function declarations:
 */

#if defined(__WIN32__) || defined(__CYGWIN__) /* WIN */
#ifndef Tcl_WinUtfToTChar
#define Tcl_WinUtfToTChar \
	(tclPlatStubsPtr->tcl_WinUtfToTChar) /* 0 */
#endif
#ifndef Tcl_WinTCharToUtf
#define Tcl_WinTCharToUtf \
	(tclPlatStubsPtr->tcl_WinTCharToUtf) /* 1 */
#endif
#endif /* WIN */
#ifdef MAC_OSX_TCL /* MACOSX */
#ifndef Tcl_MacOSXOpenBundleResources
#define Tcl_MacOSXOpenBundleResources \
	(tclPlatStubsPtr->tcl_MacOSXOpenBundleResources) /* 0 */
#endif
#ifndef Tcl_MacOSXOpenVersionedBundleResources
#define Tcl_MacOSXOpenVersionedBundleResources \
	(tclPlatStubsPtr->tcl_MacOSXOpenVersionedBundleResources) /* 1 */
#endif
#endif /* MACOSX */

#endif /* defined(USE_TCL_STUBS) && !defined(USE_TCL_STUB_PROCS) */

/* !END!: Do not edit above this line. */

#undef TCL_STORAGE_CLASS
#define TCL_STORAGE_CLASS DLLIMPORT

#endif /* _TCLPLATDECLS */


