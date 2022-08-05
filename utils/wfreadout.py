def beginWaveformStream(session,options,threshold=-1):
    if options.hbuf:
        if options.external:
            session.startDEggExternalHBufTrigStream(int(options.channel))
            return 'external-hbuf'
        elif options.threshold is not None:
            session.setDEggADCTriggerThreshold(int(options.channel),int(options.threshold))
            session.startDEggADCHBufTrigStream(int(options.channel))
            return 'threshold-hbuf'
        elif threshold > 0:
            session.setDEggADCTriggerThreshold(int(options.channel),threshold)
            session.startDEggADCHBufTrigStream(int(options.channel))
            return 'threshold-hbuf'
        else:
            print('No other available setting found.')
            return None
    else:
        if options.external:
            session.startDEggExternalTrigStream(int(options.channel))
            return 'external'
        elif threshold > 0:
            session.startDEggThreshTrigStream(int(options.channel),threshold)
            return 'threshold'
        elif options.threshold is None:
            session.startDEggSWTrigStream(int(options.channel),int(options.swTrigDelay))
            return 'software'
        else:
            session.startDEggThreshTrigStream(int(options.channel),int(options.threshold))
            return 'threshold'


