#for namespace_name in $current_class.namespace_list
namespace ${namespace_name} {
#end for

#set ClassName = $current_class.qtscript_class_name

#set has_base_parent = $current_class.base_parent is not None
#if $has_base_parent
	#set ParentClassName = $current_class.base_parent.qtscript_class_name
	#set construct_object_type = $current_class.root_base_parent.namespaced_class_name
#else
	#set native_object_type = $current_class.class_name
	#if $current_class.has_virtual_destructor
		#set $native_object_type += '* '
	#end if
	#set ParentClassName = '::QtScriptBaseClassPrototype<{}>'.format($native_object_type)
	#set construct_object_type = 'NativeObjectType'
#end if

class ${ClassName} : public ${ParentClassName}
{
	Q_OBJECT

protected:
	explicit ${ClassName}(QScriptEngine *engine, const QString &className);

	virtual int constructorArgumentCountMin() const override;
	virtual int constructorArgumentCountMax() const override;
	virtual ${construct_object_type} *constructObject(QScriptContext *) const override;

public:
	explicit ${ClassName}(QScriptEngine *engine);
	static void Register(const QScriptValue &targetNamespace);

