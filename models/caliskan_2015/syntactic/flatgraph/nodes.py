from flatgraph import Node


class MetaDataNode(Node):
    pass

# TODO: metaclass maddness
# TODO: research finding node more
# ----- Base Layer -----
class DeclarationNode(Node):
    pass


class ASTNode(Node):
    pass


class CFGNode(ASTNode):
    pass


class ExpressionNode(ASTNode, CFGNode):
    pass


# ----- File System Layer -----
class FileNode(ASTNode):
    pass


# ----- Namespace Layer ------
class NamespaceNode(ASTNode):
    pass


class NamespaceBlockNode(ASTNode):
    pass


# ----- Method Layer -----
class MethodNode(ASTNode, CFGNode, DeclarationNode):
    pass


class MethodParameterInNode(ASTNode, CFGNode, DeclarationNode):
    pass


class MethodParameterOutNode(ASTNode, CFGNode, DeclarationNode):
    pass


class MethodReturnNode(CFGNode):
    pass


# ----- Type Layer -----
class MemberNode(ASTNode, DeclarationNode):
    pass


class TypeNode:
    pass


class TypeArgumentNode(ASTNode):
    pass


class TypeDeclarationNode(ASTNode):
    pass


class TypeParameterNode(ASTNode):
    pass


# ----- AST Layer -----
class BlockNode(ExpressionNode):
    pass


class CallRepresentationNode(CFGNode):
    pass


class CallNode(CallRepresentationNode, ExpressionNode):
    pass


class ControlStructureNode(ExpressionNode):
    pass


class FieldIdentifierNode(ExpressionNode):
    pass


class IdentifierNode(ExpressionNode):
    pass


class JumpLabelNode(ASTNode):
    pass


class JumpTargetNode(ASTNode, CFGNode):
    pass


class LiteralNode(ExpressionNode):
    pass


class LocalNode(ASTNode, DeclarationNode):
    pass


class MethodReferenceNode(ExpressionNode):
    pass


class ModifierNode(ASTNode):
    pass


class ReturnNode(ExpressionNode):
    pass


class TypeReferenceNode(ExpressionNode):
    pass


class UnknownNode(ExpressionNode):
    pass


class CommentNode(ASTNode):
    pass


class FindingNode(Node):
    pass


class KeyValuePairNode(Node):
    pass


class LocationNode(Node):
    pass


class TagNode(Node):
    pass


class TagNodePairNode(Node):
    pass


class ConfigurationFileNode(Node):
    pass


class BindingNode(Node):
    pass


class AnnotationNode(ExpressionNode):
    pass


class AnnotationLiteralNode(ExpressionNode):
    pass


class AnnotationParameterNode(ASTNode):
    pass


class AnnotationParameterAssignNode(ASTNode):
    pass


class ArrayInitalizerNode(ASTNode, ExpressionNode):
    pass
