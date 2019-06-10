#for namespace_name in $current_class.namespace_list
namespace ${namespace_name} {
#end for
#set ClassName = $current_class.qtscript_class_name
#set ClassModifier = ""
#set has_base_parent = $current_class.base_parent is not None and \
	not $current_class.is_inplace_class and \
	$current_class.is_inplace_class == $current_class.base_parent.is_inplace_class
#if $has_base_parent
	#set ParentClassName = $current_class.base_parent.qtscript_class_name
#else
	#set native_object_type = $current_class.class_name
	#if $current_class.is_inplace_class
		#set $ClassModifier = "final "
	#else
		#set $native_object_type += ' *'
	#end if
	#set ParentClassName = 'QtScriptBaseClassPrototype<{}, {}>'.format($native_object_type, 'true' if $current_class.is_destructor_private else 'false')
#end if
class ${ClassName} ${ClassModifier}: public ${ParentClassName}
{
	Q_OBJECT

protected:
	explicit ${ClassName}(QScriptEngine *engine, const QByteArray &className);

	virtual int constructorArgumentCountMin() const override;
	virtual int constructorArgumentCountMax() const override;
	virtual bool constructObject(QScriptContext *, NativeObjectType &out) override;

public:
	explicit ${ClassName}(QScriptEngine *engine);
	static void Register(const QScriptValue &targetNamespace);

