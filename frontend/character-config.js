// Character Image Configuration
// Edit this file to easily swap character images without touching the main code

const CHARACTER_CONFIG = {
    bear: {
        'theme-space': 'assets/characters/bearSpaceHead.PNG',
        'theme-fantasy': 'assets/characters/bearMagicHead.PNG',
        'theme-sports': 'assets/characters/bearSportsHead.PNG',
        'theme-food': 'assets/characters/bearCookingHead.PNG',
        'theme-creative': 'assets/characters/bearArtHead.PNG',
        'theme-whimsical': 'assets/characters/bearMagicHead.PNG', // Use magic for whimsical
        'theme-ocean': 'assets/characters/bearOceanHead.PNG', // Now has specific ocean head
        'theme-animals': 'assets/characters/bearFallbackHead.PNG', // Use ocean for animals/nature
        'theme-elegant': 'assets/characters/bearFallbackHead.png', // Use fallback for professional
        'theme-fun': 'assets/characters/bearSpaceHead.PNG', // Use space for fun
        'fallback': 'assets/characters/bearFallbackHead.png'
    },
    boy: {
        'theme-space': 'assets/characters/boySpaceHead.png',
        'theme-sports': 'assets/characters/boySportsHead.png', 
        'theme-ocean': 'assets/characters/boyOceanHead.png',
        'theme-animals': 'assets/characters/boyDefault.png', // Use ocean for animals/nature
        'theme-fantasy': 'assets/characters/boyDefault.png', // No specific fantasy head yet
        'theme-whimsical': 'assets/characters/boyDefault.png', // No specific whimsical head yet
        'theme-food': 'assets/characters/boyDefault.png', // No specific food head yet
        'theme-creative': 'assets/characters/boyDefault.png', // No specific creative head yet
        'theme-elegant': 'assets/characters/boyDefault.png', // No specific elegant head yet
        'theme-fun': 'assets/characters/boySpaceHead.png', // Use space for fun
        'fallback': 'assets/characters/boyDefault.png'
    }
};

// Easy function to get character image path
function getCharacterImage(characterType, theme) {
    const config = CHARACTER_CONFIG[characterType];
    if (!config) return CHARACTER_CONFIG.boy.fallback; // Default fallback
    
    return config[theme] || config.fallback || CHARACTER_CONFIG.boy.fallback;
}