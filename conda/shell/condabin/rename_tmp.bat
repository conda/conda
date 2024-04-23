:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Rename src to dest

@pushd "%1"
@ren "%2" "%3" > NUL 2> NUL
