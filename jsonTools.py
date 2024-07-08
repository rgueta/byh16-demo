import json
timestamp = ''

########################################################
# mov       -> movement c:crate, r:read, u:update, d:delete, updLock: lock user, updUnlock:unlock user
# file      -> json file name to update
# key       -> key to find
# value     -> value to change
# newValue  -> new value to change previous value
# wholeWord -> If Find whole word or part of it, default True [yes find whole word]
# return key-> return value from key, default = '' ignore return key, return '' if key not exist
# Desc: Generic Module [crud] for JSON files
#######################################################33
def updJson(mov, file, key, value, newValue = '', wholeWord = True, returnKey = '', timestamp = ''):
    global jcodes
    global code_list
    global restraint_list
    global config
    global openByCode
    try:
        jsonObj = open(file, "r")
        file_list = json.loads(jsonObj.read())
        jsonObj.close()

        for item in file_list:
            if item == key: # found at first level
                if mov == 'r': #read
                    if file_list[item][key] == value:
                        print('si existe key -->',item, ', with value -> ', value)
                        break
                elif mov == 'd':   # delete
                    print('Delete action pending key -->',item,' : ',file_list[key],' with --> ', value)
                    break
                elif mov == 'c':   # create
                    file_list[key].append(value)
                    jfiles = open(file,'w')
                    json.dump(file_list,jfiles)
                    jfiles.close()
                    break
                elif mov == 'u':   # update
                    file_list[key][value] = newValue
                    f = open(file,"w")
                    json.dump(file_list, f)
                    f.close()
                    break
                break
            for j, jitem in enumerate(file_list[item]): # looking in 2nd level
                if jitem == key: #found key in 2nd level
                    if mov == 'r':   # read
                        print('Read action pending key --> ',jitem,' : ',file_list[item][key],' with --> ', value)
                        break
                    elif mov == 'd':   # delete
                        print('Delete action pending key --> ',jitem,' : ',file_list[item][key],' with --> ', value)
                        break
                    elif mov == 'c':   # create
                        print('Insert action pending key -> ',jitem,' : ',file_list[item],' with --> ', value)
                        break
                    elif mov == 'u':   # update
                        print('file_list[jitem]  -> ', file_list[jitem]);
                        print('upd action key, value, newValue -> ', key,', ', value, ', ', newValue);
                        file_list[jitem] = value
                        f = open(file,"w")
                        json.dump(file_list, f)
                        f.close()
                        break

                 # when jitem is string  -------------------------------------------
                if type(jitem) == 'str':
                    for k,kitem in enumerate(file_list[item][jitem]):
                        print('kitem -> ', kitem)
                        if kitem == key:
                            if mov == 'r':   # Read
                                print('Read action pending kitem -->',kitem,' : ',file_list[item][jitem][key],' with --> ', value)
                                break
                            elif mov == 'd':   # delete
                                print('Delete action pending kitem -->',kitem,' : ',file_list[item][jitem][key],' with --> ', value)
                                break
                            elif mov == 'c':   # create
                                print('Insert action pending kitem -->',kitem,' : ',file_list[item][jitem][key],' with --> ', value)
                                break
                            elif mov == 'u':   # update
                                print('Change action pending kitem -->',kitem,' : ',file_list[item][jitem][key],' with --> ', value)
                                break
                            break

                # when jitem found as array  -------------------------------------------
                elif (type(jitem) != 'int' or type(jitem) != 'float' or type(jitem) != 'str') :
                    for l,dict in enumerate(jitem):
                        if dict == key:
                            found = False
                            if len(jitem[dict]) == len(value):
                                 if jitem[dict] == value:
                                    found = True
                            else:        
                                if wholeWord:
                                    if jitem[dict] == value:
                                        found = True
                                else:
                                    if len(jitem[dict]) < len(value):
                                        if jitem[dict] in value:
                                            found = True
                                    else:
                                        if value in jitem[dict]:
                                            found = True
                            if found:
                                if mov == 'updStatus':
                                    if file_list[item][j]['sim'] == value:
                                        file_list[item][j]['status'] = newValue
                                        file_list[item][j]['updatedAt'] = timestamp
                                        wfile = open(file,'w')
                                        json.dump(file_list, wfile)
                                        wfile.close()
                                        break

                                if mov == 'updSim':
                                     if file_list[item][j]['sim'] == value:
                                        file_list[item][j]['sim'] = newValue
                                        file_list[item][j]['updatedAt'] = timestamp
                                        wfile = open(file,'w')
                                        json.dump(file_list, wfile)
                                        wfile.close()
                                        break
                                
                                if mov == 'delete':
                                     if file_list[item][j]['id'] == value:
                                        del file_list[item][j]
                                        wfile = open(file,'w')
                                        json.dump(file_list, wfile)
                                        wfile.close()
                                        break

                                if newValue == '': # not require change value
                                    if mov == 'r':   #read
                                        if returnKey == '':
                                            return True
                                            break
                                        else:
                                            if jitem[returnKey]:
                                                return jitem[returnKey]
                                                break
                                            else:
                                                return ''
                                                break
                                            
                                    elif mov == 'd':   # delete
                                        del file_list[item][j]
                                        f = open(file,"w")
                                        json.dump(file_list, f)
                                        f.close()

                                        break
                                    elif mov == 'c':   # create
                                        print('Insert action pending index:', j, ' jitem -> ',file_list[item][j])
                                        break
                                    elif mov == 'u':   # update
                                        print('Change action pending index:', j, ' jitem -> ',file_list[item][j])
                                        break

                                else:
                                    for m, e in enumerate(file_list[item]):
                                        if e[key] == value and mov == 'u': # update
                                            print('last upd action key, value, newValue -> ', 
                                                    key,', ', value, ', ', newValue);
                                            file_list[item][m][key] = newValue
                                            f = open(file,"w")
                                            json.dump(file_list, f)
                                            f.close()
                                            break
            if mov != 'r':                                
                if file == 'codes.json':
                    jcodes = open('codes.json')
                    code_list = json.loads(jcodes.read())
                    jcodes.close()
                    return
                elif file == 'restraint.json':
                    jfiles = open('restraint.json', 'r')
                    restraint_list = json.loads(jfiles.read())
                    jfiles.close()
                    return
                elif file == 'config.json':
                    jfiles = open('config.json')
                    config = json.loads(jfiles.read())
                    jfiles.close()
                    openByCode = config['app']['openByCode']
                    return

    except (TypeError) as err:  # create file not exists
        print('InsertJson Error --> ', file, ', ', err)
        pass    


def getLocalTimestamp():
    global timestamp
    tsf = ((str(timestamp[0:2]) + '-' + str(timestamp[3:5]) + '-' +
          str(timestamp[6:8]) + 'T' + str(timestamp[9:11]) + ':' +
          str(timestamp[12:14]) + ':' + str(timestamp[15:17])))
    return tsf

if __name__ == "__main__" :
    print("Running at tools.py")